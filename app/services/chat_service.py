from collections.abc import Generator
import logging
from difflib import SequenceMatcher

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.models.schemas import ChatResponse
from app.services.retriever import HybridRetriever

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a precise document assistant.
Answer only from the provided context when possible.
If the answer is not grounded in the retrieved context, say what is missing.
Keep answers beginner-friendly but technically strong.
Always cite source file names and page numbers when available.
"""


class ChatService:
    def __init__(self, retriever: HybridRetriever) -> None:
        self.settings = get_settings()
        if not self.settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for chat generation")
        self.retriever = retriever
        self.llm = ChatGroq(
            api_key=self.settings.groq_api_key,
            model=self.settings.groq_model,
            temperature=0.2,
            streaming=True,
        )

    def rewrite_query(self, question: str) -> str:
        if not self.settings.enable_query_rewrite:
            return question

        prompt = [
            SystemMessage(
                content=(
                    "Rewrite the user question into a concise retrieval query. "
                    "Return only the rewritten query."
                )
            ),
            HumanMessage(content=question),
        ]
        return self.llm.invoke(prompt).content.strip()

    def expand_query(self, rewritten_query: str) -> list[str]:
        if not self.settings.enable_query_expansion:
            return [rewritten_query]
        variants = max(1, self.settings.query_expansion_variants)
        prompt = [
            SystemMessage(
                content=(
                    f"Generate {variants} diverse search query variants for retrieval. "
                    "Return one query per line and no extra text."
                )
            ),
            HumanMessage(content=rewritten_query),
        ]
        content = self.llm.invoke(prompt).content.strip()
        lines = [item.strip("- ").strip() for item in content.splitlines() if item.strip()]
        if not lines:
            return [rewritten_query]
        deduped = []
        seen = set()
        for line in [rewritten_query] + lines:
            if line.lower() not in seen:
                deduped.append(line)
                seen.add(line.lower())
        return deduped[: variants + 1]

    def answer(
        self, user_id: str, question: str, chat_history: list[dict[str, str]], top_k: int | None
    ) -> ChatResponse:
        """Generate an answer without streaming."""
        try:
            logger.info(f"Answering question for user {user_id}")
            rewritten_query = self.rewrite_query(question)
            query_variants = self.expand_query(rewritten_query)
            documents, debug = self.retriever.retrieve(user_id=user_id, queries=query_variants, k=top_k)
            answer = self._invoke_llm(question, chat_history, documents)
            sources = self.retriever.to_sources(documents)
            logger.info(f"Answer generated with {len(sources)} sources")
            return ChatResponse(
                answer=answer,
                rewritten_query=rewritten_query,
                query_variants=query_variants,
                sources=sources,
                retrieval_debug=debug,
            )
        except Exception as exc:
            logger.error(f"Answer generation failed: {str(exc)}", exc_info=True)
            raise

    def stream_answer(
        self, user_id: str, question: str, chat_history: list[dict[str, str]], top_k: int | None
    ) -> Generator[dict, None, None]:
        """Generate an answer with streaming."""
        try:
            logger.info(f"Streaming answer for user {user_id}")
            rewritten_query = self.rewrite_query(question)
            query_variants = self.expand_query(rewritten_query)
            documents, debug = self.retriever.retrieve(user_id=user_id, queries=query_variants, k=top_k)
            sources = self.retriever.to_sources(documents)

            yield {
                "event": "meta",
                "data": {
                    "rewritten_query": rewritten_query,
                    "query_variants": query_variants,
                    "sources": [s.model_dump() for s in sources],
                    "retrieval_debug": debug,
                },
            }

            messages = self._build_messages(question, chat_history, documents)
            for chunk in self.llm.stream(messages):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    yield {"event": "token", "data": text}

            logger.info("Stream completed successfully")
            yield {"event": "done", "data": "completed"}
        except Exception as exc:
            logger.error(f"Stream generation failed: {str(exc)}", exc_info=True)
            yield {"event": "error", "data": str(exc)}

    def evaluate(
        self,
        user_id: str,
        question: str,
        expected_answer: str | None,
        chat_history: list[dict[str, str]],
        top_k: int | None,
    ) -> dict:
        response = self.answer(user_id=user_id, question=question, chat_history=chat_history, top_k=top_k)
        metrics = self._evaluate_metrics(response.answer, expected_answer, response.sources)
        return {
            "answer": response.answer,
            "rewritten_query": response.rewritten_query,
            "query_variants": response.query_variants,
            "metrics": metrics,
            "sources": response.sources,
            "retrieval_debug": response.retrieval_debug,
        }

    def _evaluate_metrics(self, answer: str, expected_answer: str | None, sources: list) -> dict[str, float]:
        answer_similarity = 0.0
        if expected_answer:
            answer_similarity = SequenceMatcher(None, answer.lower(), expected_answer.lower()).ratio()

        grounded = 0
        answer_tokens = set(answer.lower().split())
        for source in sources:
            excerpt_tokens = set(source.excerpt.lower().split())
            if answer_tokens & excerpt_tokens:
                grounded += 1
        context_precision = grounded / max(1, len(sources))
        return {
            "answer_similarity": round(answer_similarity, 4),
            "context_precision": round(context_precision, 4),
            "retrieved_sources": float(len(sources)),
        }

    def _invoke_llm(self, question: str, chat_history: list[dict[str, str]], documents: list[Document]) -> str:
        messages = self._build_messages(question, chat_history, documents)
        response = self.llm.invoke(messages)
        return response.content

    def _build_messages(
        self, question: str, chat_history: list[dict[str, str]], documents: list[Document]
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        context = self._format_context(documents)
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=f"{SYSTEM_PROMPT}\n\nContext:\n{context}")
        ]

        for turn in chat_history[-6:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=question))
        return messages

    def _format_context(self, documents: list[Document]) -> str:
        formatted_chunks = []
        for doc in documents:
            page = doc.metadata.get("page")
            formatted_chunks.append(
                f"[Source: {doc.metadata.get('file_name')} | Page: {page}]\n{doc.page_content}"
            )
        return "\n\n".join(formatted_chunks)

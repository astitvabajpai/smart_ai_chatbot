import math
import re
from collections import defaultdict

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.models.schemas import SourceChunk
from app.services.vector_store import VectorStoreService


class HybridRetriever:
    def __init__(self, vector_store_service: VectorStoreService) -> None:
        self.settings = get_settings()
        self.vector_store_service = vector_store_service

    def retrieve(self, user_id: str, queries: list[str], k: int | None = None) -> tuple[list[Document], dict]:
        top_k = k or self.settings.top_k
        dense_results: list[tuple[Document, float]] = []
        for query in queries:
            dense_results.extend(
                self.vector_store_service.similarity_search(
                    user_id=user_id,
                    query=query,
                    k=top_k * 2,
                )
            )
        deduped_dense: dict[str, tuple[Document, float]] = {}
        for doc, score in dense_results:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id not in deduped_dense or deduped_dense[chunk_id][1] < score:
                deduped_dense[chunk_id] = (doc, score)
        dense_results = list(deduped_dense.values())

        if not self.settings.enable_hybrid_search:
            documents = [doc for doc, _score in dense_results[:top_k]]
            debug = {"strategy": "dense_only", "dense_hits": len(dense_results)}
            return documents, debug

        indexed_records = self.vector_store_service.load_index_state(user_id=user_id)
        bm25_docs = [record["page_content"] for record in indexed_records]
        dense_score_map = {
            doc.metadata.get("chunk_id"): self._normalize_score(score) for doc, score in dense_results
        }

        bm25_score_map: dict[str, float] = {}
        if bm25_docs:
            tokens = [self._tokenize(text) for text in bm25_docs]
            bm25 = BM25Okapi(tokens)
            for query in queries:
                scores = bm25.get_scores(self._tokenize(query))
                for record, score in zip(indexed_records, scores, strict=False):
                    chunk_id = record["metadata"].get("chunk_id")
                    bm25_score_map[chunk_id] = max(bm25_score_map.get(chunk_id, 0.0), float(score))

        combined = defaultdict(float)
        doc_lookup: dict[str, Document] = {doc.metadata.get("chunk_id"): doc for doc, _ in dense_results}

        for chunk_id, score in dense_score_map.items():
            combined[chunk_id] += 0.7 * score
        for record in indexed_records:
            chunk_id = record["metadata"].get("chunk_id")
            if chunk_id not in doc_lookup:
                doc_lookup[chunk_id] = Document(
                    page_content=record["page_content"],
                    metadata=record["metadata"],
                )
        max_bm25 = max(bm25_score_map.values(), default=1.0) or 1.0
        for chunk_id, score in bm25_score_map.items():
            combined[chunk_id] += 0.3 * (score / max_bm25)

        ranked_ids = sorted(combined.keys(), key=lambda item: combined[item], reverse=True)[:top_k]
        ranked_docs = [doc_lookup[chunk_id] for chunk_id in ranked_ids if chunk_id in doc_lookup]

        debug = {
            "strategy": "hybrid",
            "dense_hits": len(dense_results),
            "lexical_hits": len(bm25_score_map),
            "top_chunk_ids": ranked_ids,
            "query_count": len(queries),
        }
        return ranked_docs, debug

    def to_sources(self, documents: list[Document]) -> list[SourceChunk]:
        sources: list[SourceChunk] = []
        for doc in documents:
            sources.append(
                SourceChunk(
                    document_id=doc.metadata.get("document_id", "unknown"),
                    file_name=doc.metadata.get("file_name", "unknown"),
                    page=doc.metadata.get("page"),
                    chunk_id=doc.metadata.get("chunk_id", "unknown"),
                    excerpt=doc.page_content[:300].strip(),
                )
            )
        return sources

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _normalize_score(self, score: float) -> float:
        if math.isnan(score):
            return 0.0
        return max(0.0, min(1.0, score))

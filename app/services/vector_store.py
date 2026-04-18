import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import get_settings
from app.services.embeddings import build_embeddings


class VectorStoreService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._embeddings = build_embeddings()
        self._stores: dict[str, Any] = {}

    def add_documents(self, user_id: str, documents: list[Document]) -> int:
        ids: list[str] = []
        for index, doc in enumerate(documents):
            doc.metadata["chunk_id"] = f"{doc.metadata.get('document_id', 'doc')}-{index}"
            doc.metadata["chunk_index"] = index
            doc.metadata["user_id"] = user_id
            ids.append(doc.metadata["chunk_id"])
        store = self._store_for_user(user_id)
        store.add_documents(documents, ids=ids)
        self._append_index_state(user_id, documents)
        return len(documents)

    def similarity_search(self, user_id: str, query: str, k: int) -> list[tuple[Document, float]]:
        store = self._store_for_user(user_id)
        return store.similarity_search_with_relevance_scores(query, k=k)

    def _store_for_user(self, user_id: str):
        if user_id in self._stores:
            return self._stores[user_id]

        backend = self.settings.vector_backend.lower().strip()
        if backend == "pinecone":
            store = self._build_pinecone_store(user_id)
        elif backend == "qdrant":
            store = self._build_qdrant_store(user_id)
        else:
            store = self._build_chroma_store(user_id)
        self._stores[user_id] = store
        return store

    def _build_chroma_store(self, user_id: str):
        from langchain_chroma import Chroma

        collection_name = f"document_chatbot_{user_id}"
        return Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            persist_directory=str(self.settings.chroma_dir),
        )

    def _build_pinecone_store(self, user_id: str):
        from langchain_pinecone import PineconeVectorStore
        from pinecone import Pinecone, ServerlessSpec

        if not self.settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required when VECTOR_BACKEND=pinecone")
        if not self.settings.pinecone_index:
            raise ValueError("PINECONE_INDEX is required when VECTOR_BACKEND=pinecone")
        pc = Pinecone(api_key=self.settings.pinecone_api_key)
        index_name = self.settings.pinecone_index
        listed = pc.list_indexes()
        if hasattr(listed, "names"):
            existing = listed.names()
        else:
            existing = [item.get("name") for item in listed]
        if index_name not in existing:
            pc.create_index(
                name=index_name,
                dimension=self.settings.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        index = pc.Index(index_name)
        namespace = f"{self.settings.pinecone_namespace_prefix}-{user_id}"
        return PineconeVectorStore(
            index=index,
            embedding=self._embeddings,
            namespace=namespace,
        )

    def _build_qdrant_store(self, user_id: str):
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        collection_name = f"{self.settings.qdrant_collection_prefix}_{user_id.replace('-', '_')}"
        client = QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)
        existing = [item.name for item in client.get_collections().collections]
        if collection_name not in existing:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=self._embeddings,
        )

    def _append_index_state(self, user_id: str, documents: list[Document]) -> None:
        state = self._load_state()
        user_rows = state.get(user_id, [])
        deduped = {
            item["metadata"].get("chunk_id"): item
            for item in user_rows
            if item.get("metadata", {}).get("chunk_id")
        }
        for doc in documents:
            deduped[doc.metadata["chunk_id"]] = {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
        state[user_id] = list(deduped.values())
        self._write_state(state)

    def load_index_state(self, user_id: str) -> list[dict[str, Any]]:
        state = self._load_state()
        return state.get(user_id, [])

    def _load_state(self) -> dict[str, list[dict[str, Any]]]:
        state_path = Path(self.settings.index_state_path)
        if not state_path.exists():
            return {}
        return json.loads(state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, list[dict[str, Any]]]) -> None:
        state_path = Path(self.settings.index_state_path)
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

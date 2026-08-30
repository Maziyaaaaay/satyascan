import asyncio
from typing import List, Optional

from app.vectorstore.base import VectorStore, VectorStoreItem, VectorStoreMatch


class ChromaStore(VectorStore):
    """Local, embedded vector store backed by chromadb's PersistentClient.

    Deliberately never uses Chroma's default embedding function (which pulls
    in onnxruntime and downloads a model on first use) - every upsert/query
    call must be given explicit embeddings from LLMProvider.embed(), real or
    mock, so this stays lightweight and fully offline-testable.
    """

    def __init__(self, persist_dir: str):
        self._persist_dir = persist_dir
        self._client = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            # Privacy-first: never phone home, per Part 12's principles.
            self._client = chromadb.PersistentClient(
                path=self._persist_dir, settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    def _get_collection(self, name: str):
        client = self._get_client()
        return client.get_or_create_collection(name=name, embedding_function=None)

    async def upsert(self, collection: str, items: List[VectorStoreItem]) -> None:
        if not items:
            return

        def _call():
            coll = self._get_collection(collection)
            coll.upsert(
                ids=[item.id for item in items],
                embeddings=[item.embedding for item in items],
                documents=[item.text for item in items],
                # Chroma rejects {} as metadata (must be a non-empty dict or None)
                metadatas=[item.metadata or None for item in items],
            )

        await asyncio.to_thread(_call)

    async def query(self, collection: str, embedding: List[float], top_k: int = 5) -> List[VectorStoreMatch]:
        def _call() -> Optional[dict]:
            coll = self._get_collection(collection)
            if coll.count() == 0:
                return None
            return coll.query(query_embeddings=[embedding], n_results=min(top_k, coll.count()))

        result = await asyncio.to_thread(_call)
        if result is None:
            return []

        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        return [
            VectorStoreMatch(id=ids[i], text=documents[i], metadata=metadatas[i] or {}, distance=distances[i])
            for i in range(len(ids))
        ]

    async def delete_collection(self, collection: str) -> None:
        def _call():
            client = self._get_client()
            try:
                client.delete_collection(name=collection)
            except Exception:
                # Chroma raises if the collection doesn't exist (e.g. this
                # verification had no evidence to upsert in the first
                # place) - deleting something already-absent is a no-op as
                # far as the caller is concerned, not a real failure.
                pass

        await asyncio.to_thread(_call)

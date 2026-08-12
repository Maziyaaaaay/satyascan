from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic import BaseModel


class VectorStoreItem(BaseModel):
    id: str
    text: str
    embedding: List[float]
    metadata: Dict = {}


class VectorStoreMatch(BaseModel):
    id: str
    text: str
    metadata: Dict
    distance: float


class VectorStore(ABC):
    """Embeddings-based similarity search, used by the Evidence Ranking agent
    for semantic de-duplication/scoring. Embeddings are always supplied by
    the caller (via LLMProvider.embed) - implementations must never compute
    their own, so mock and real LLM providers behave identically here."""

    @abstractmethod
    async def upsert(self, collection: str, items: List[VectorStoreItem]) -> None: ...

    @abstractmethod
    async def query(self, collection: str, embedding: List[float], top_k: int = 5) -> List[VectorStoreMatch]: ...

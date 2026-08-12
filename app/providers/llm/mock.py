import hashlib
from typing import List, Optional, Type

from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse
from app.providers.llm._fake_schema import fake_instance

EMBEDDING_DIM = 16


class MockLLMProvider(LLMProvider):
    """Deterministic, network-free stand-in for Gemini/OpenAI. Given the same
    prompt it always returns the same output, so pipeline/integration tests
    are stable without any external account."""

    def __init__(self) -> None:
        self.calls: List[dict] = []

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        seed = hashlib.sha256(f"{system_prompt}\n{user_prompt}".encode("utf-8")).hexdigest()

        if response_schema is not None:
            instance = fake_instance(response_schema, seed=seed)
            return LLMResponse(
                text=instance.model_dump_json(),
                parsed=instance.model_dump(mode="json"),
                model="mock-llm",
                is_mock=True,
            )

        return LLMResponse(text=f"[mock response for seed {seed[:8]}]", model="mock-llm", is_mock=True)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([(digest[i % len(digest)] / 255.0) for i in range(EMBEDDING_DIM)])
        return vectors

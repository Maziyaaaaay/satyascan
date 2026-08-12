import enum
from typing import List, Optional

import pytest
from pydantic import BaseModel

from app.providers.base import LLMProvider
from app.providers.llm.mock import MockLLMProvider


class _Rating(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class _DemoSchema(BaseModel):
    label: str
    score: float
    is_relevant: bool
    rating: _Rating
    tags: List[str]
    note: Optional[str] = None


@pytest.mark.asyncio
async def test_mock_llm_is_an_llm_provider():
    assert isinstance(MockLLMProvider(), LLMProvider)


@pytest.mark.asyncio
async def test_generate_without_schema_returns_deterministic_text():
    provider = MockLLMProvider()
    r1 = await provider.generate(system_prompt="sys", user_prompt="hello")
    r2 = await provider.generate(system_prompt="sys", user_prompt="hello")
    assert r1.text == r2.text
    assert r1.is_mock is True
    assert r1.parsed is None


@pytest.mark.asyncio
async def test_generate_with_schema_returns_valid_deterministic_instance():
    provider = MockLLMProvider()
    r1 = await provider.generate(system_prompt="sys", user_prompt="claim X", response_schema=_DemoSchema)
    r2 = await provider.generate(system_prompt="sys", user_prompt="claim X", response_schema=_DemoSchema)

    assert r1.parsed == r2.parsed
    instance = _DemoSchema.model_validate(r1.parsed)
    assert 0.0 <= instance.score <= 1.0
    assert isinstance(instance.rating, _Rating)
    assert len(instance.tags) >= 1

    r3 = await provider.generate(system_prompt="sys", user_prompt="claim Y", response_schema=_DemoSchema)
    assert r3.parsed != r1.parsed


@pytest.mark.asyncio
async def test_embed_is_deterministic_and_dimension_matches():
    provider = MockLLMProvider()
    v1 = await provider.embed(["hello world"])
    v2 = await provider.embed(["hello world"])
    v3 = await provider.embed(["a different string"])

    assert v1 == v2
    assert v1 != v3
    assert len(v1[0]) > 0
    assert all(0.0 <= x <= 1.0 for x in v1[0])


@pytest.mark.asyncio
async def test_generate_records_calls():
    provider = MockLLMProvider()
    await provider.generate(system_prompt="sys", user_prompt="hi")
    assert len(provider.calls) == 1
    assert provider.calls[0]["user_prompt"] == "hi"

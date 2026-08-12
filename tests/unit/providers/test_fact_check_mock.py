import pytest

from app.providers.base import FactCheckProvider
from app.providers.fact_check.mock import MockFactCheckProvider


@pytest.mark.asyncio
async def test_mock_fact_check_is_a_fact_check_provider():
    assert isinstance(MockFactCheckProvider(), FactCheckProvider)


@pytest.mark.asyncio
async def test_search_claims_always_returns_at_least_one_result():
    provider = MockFactCheckProvider()
    results = await provider.search_claims("drinking hot water cures COVID")
    assert len(results) >= 1
    assert all(r.claim_text for r in results)
    assert all(r.url and r.url.startswith("https://") for r in results)


@pytest.mark.asyncio
async def test_search_claims_is_deterministic():
    provider = MockFactCheckProvider()
    r1 = await provider.search_claims("same query")
    r2 = await provider.search_claims("same query")
    assert [r.model_dump() for r in r1] == [r.model_dump() for r in r2]

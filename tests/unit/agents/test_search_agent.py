import pytest

from app.agents import search_agent
from app.agents.state import ExtractedClaim


@pytest.mark.asyncio
async def test_search_returns_fact_checks_for_claims(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="drinking hot water cures COVID")]
    result = await search_agent.run(base_state, providers)
    assert result.search is not None
    assert len(result.search.fact_checks) >= 1


@pytest.mark.asyncio
async def test_no_claims_returns_empty_search_result(base_state, providers):
    result = await search_agent.run(base_state, providers)
    assert result.search.fact_checks == []

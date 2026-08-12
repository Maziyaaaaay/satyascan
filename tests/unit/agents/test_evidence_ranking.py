import pytest

from app.agents import evidence_ranking
from app.agents.state import ExtractedClaim, SearchResult
from app.providers.base import FactCheckResult


@pytest.mark.asyncio
async def test_ranks_evidence_from_fact_checks(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="hot water cures covid")]
    base_state.search = SearchResult(
        fact_checks=[
            FactCheckResult(claim_text="hot water cures covid", rating="False", publisher="Alt News", url="https://a.example/1"),
            FactCheckResult(claim_text="hot water cures covid", rating="True", publisher="Boom", url="https://b.example/2"),
        ]
    )
    result = await evidence_ranking.run(base_state, providers)
    assert len(result.ranked_evidence) == 2
    assert {e.rank for e in result.ranked_evidence} == {1, 2}
    assert all(0.0 <= e.relevance_score <= 1.0 for e in result.ranked_evidence)
    assert {e.stance.value for e in result.ranked_evidence} == {"contradicts", "supports"}


@pytest.mark.asyncio
async def test_no_evidence_sources_returns_empty_list(base_state, providers):
    result = await evidence_ranking.run(base_state, providers)
    assert result.ranked_evidence == []

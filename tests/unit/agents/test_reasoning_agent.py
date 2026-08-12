import pytest

from app.agents import reasoning_agent
from app.agents.state import ExtractedClaim, RankedEvidence
from app.models.enums import Stance, Verdict


@pytest.mark.asyncio
async def test_produces_valid_verdict_and_bounded_certainty(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="hot water cures covid")]
    base_state.ranked_evidence = [
        RankedEvidence(claim_snippet="False: ...", stance=Stance.contradicts, relevance_score=0.9, rank=1)
    ]
    result = await reasoning_agent.run(base_state, providers)
    assert isinstance(result.reasoning.verdict, Verdict)
    assert 0.0 <= result.reasoning.certainty <= 1.0
    assert result.reasoning.rationale


@pytest.mark.asyncio
async def test_handles_no_evidence_gracefully(base_state, providers):
    base_state.input_text = "some unverifiable claim"
    result = await reasoning_agent.run(base_state, providers)
    assert isinstance(result.reasoning.verdict, Verdict)

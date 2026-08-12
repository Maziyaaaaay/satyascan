import pytest

from app.agents import confidence_scoring
from app.agents.state import RankedEvidence, ReasoningResult
from app.models.enums import ConfidenceLabel, Stance, Verdict


@pytest.mark.asyncio
async def test_no_evidence_yields_low_confidence(base_state, providers):
    base_state.reasoning = ReasoningResult(verdict=Verdict.unverifiable, rationale="no evidence", certainty=0.1)
    base_state.ranked_evidence = []
    result = await confidence_scoring.run(base_state, providers)
    assert result.confidence.label == ConfidenceLabel.low
    assert 0.0 <= result.confidence.score <= 1.0


@pytest.mark.asyncio
async def test_strong_consistent_evidence_yields_high_confidence(base_state, providers):
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="strong contradiction", certainty=0.95)
    base_state.ranked_evidence = [
        RankedEvidence(claim_snippet="a", stance=Stance.contradicts, relevance_score=0.95, rank=1),
        RankedEvidence(claim_snippet="b", stance=Stance.contradicts, relevance_score=0.9, rank=2),
    ]
    result = await confidence_scoring.run(base_state, providers)
    assert result.confidence.label == ConfidenceLabel.high
    assert result.confidence.score > 0.7


@pytest.mark.asyncio
async def test_contradictory_evidence_yields_lower_confidence_than_consistent(base_state, providers):
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="mixed", certainty=0.5)
    base_state.ranked_evidence = [
        RankedEvidence(claim_snippet="a", stance=Stance.supports, relevance_score=0.9, rank=1),
    ]
    result = await confidence_scoring.run(base_state, providers)
    assert result.confidence.score < 0.5

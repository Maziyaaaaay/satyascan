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


@pytest.mark.asyncio
async def test_live_search_confirmation_is_not_drowned_out_by_tangential_evidence(base_state, providers):
    # Regression case for a real bug: one directly-on-point live-search
    # result confirming the verdict, outnumbered 8-to-1 by older,
    # topically-adjacent-but-irrelevant fact-checks (e.g. debunked videos
    # that merely mention the same subject). The sheer count of "contradicts"
    # items must not suppress confidence below what a direct confirmation
    # from live search deserves.
    base_state.reasoning = ReasoningResult(verdict=Verdict.true, rationale="confirmed by live search", certainty=0.8)
    base_state.ranked_evidence = [
        RankedEvidence(claim_snippet="live", stance=Stance.supports, relevance_score=0.67, rank=1, is_live_search=True)
    ] + [
        RankedEvidence(claim_snippet=f"old {i}", stance=Stance.contradicts, relevance_score=0.4, rank=i + 2)
        for i in range(8)
    ]
    result = await confidence_scoring.run(base_state, providers)
    assert result.confidence.label == ConfidenceLabel.high


@pytest.mark.asyncio
async def test_live_search_with_wrong_stance_does_not_trigger_floor(base_state, providers):
    # The floor only applies when the live-search evidence actually matches
    # the verdict direction - it must not blindly boost confidence just
    # because a live-search item exists in the pool.
    base_state.reasoning = ReasoningResult(verdict=Verdict.true, rationale="mixed", certainty=0.5)
    base_state.ranked_evidence = [
        RankedEvidence(
            claim_snippet="live", stance=Stance.contradicts, relevance_score=0.67, rank=1, is_live_search=True
        ),
    ]
    result = await confidence_scoring.run(base_state, providers)
    assert result.confidence.score < 0.85

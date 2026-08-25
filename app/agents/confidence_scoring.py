from app.agents.state import ConfidenceResult, PipelineState
from app.models.enums import ConfidenceLabel, Stance, Verdict
from app.providers.bundle import Providers

NO_EVIDENCE_COMPONENT = 0.3
EVIDENCE_WEIGHT = 0.6
RELEVANCE_WEIGHT = 0.6
EVIDENCE_COMPONENT_WEIGHT = 0.5
CERTAINTY_WEIGHT = 0.5
HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4

# A live web search result that itself matches the verdict direction is a
# direct, current, on-topic signal - the strongest kind of evidence this
# pipeline can get for "who/what currently holds X" claims. Confirmed live
# that without this floor, a handful of tangential old fact-checks (e.g.
# debunked videos that merely *mention* the same subject) can outnumber
# that one directly-on-point result and drag stance_ratio down via sheer
# count, capping confidence at "medium" even when the verdict is correct
# and well-supported.
LIVE_SEARCH_CONFIRMED_FLOOR = 0.85


def _label_for(score: float) -> ConfidenceLabel:
    if score >= HIGH_THRESHOLD:
        return ConfidenceLabel.high
    if score >= MEDIUM_THRESHOLD:
        return ConfidenceLabel.medium
    return ConfidenceLabel.low


def _evidence_component(state: PipelineState) -> float:
    evidence = state.ranked_evidence
    if not evidence:
        return NO_EVIDENCE_COMPONENT

    verdict = state.reasoning.verdict
    if verdict in (Verdict.false, Verdict.misleading):
        consistent = [e for e in evidence if e.stance == Stance.contradicts]
    elif verdict == Verdict.true:
        consistent = [e for e in evidence if e.stance == Stance.supports]
    else:
        consistent = evidence

    stance_ratio = len(consistent) / len(evidence)
    avg_relevance = sum(e.relevance_score for e in evidence) / len(evidence)
    score = EVIDENCE_WEIGHT * stance_ratio + (1 - EVIDENCE_WEIGHT) * avg_relevance

    if any(e.is_live_search for e in consistent):
        score = max(score, LIVE_SEARCH_CONFIRMED_FLOOR)

    return score


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    """Deliberately rule-based, not an LLM call - fast, cheap, and fully
    deterministic since this is the last quantitative gate before the
    explanation is rendered."""
    evidence_component = _evidence_component(state)
    score = EVIDENCE_COMPONENT_WEIGHT * evidence_component + CERTAINTY_WEIGHT * state.reasoning.certainty
    score = round(min(1.0, max(0.0, score)), 4)
    state.confidence = ConfidenceResult(score=score, label=_label_for(score))
    return state

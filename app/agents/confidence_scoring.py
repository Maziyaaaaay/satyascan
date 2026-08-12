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
    return EVIDENCE_WEIGHT * stance_ratio + (1 - EVIDENCE_WEIGHT) * avg_relevance


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    """Deliberately rule-based, not an LLM call - fast, cheap, and fully
    deterministic since this is the last quantitative gate before the
    explanation is rendered."""
    evidence_component = _evidence_component(state)
    score = EVIDENCE_COMPONENT_WEIGHT * evidence_component + CERTAINTY_WEIGHT * state.reasoning.certainty
    score = round(min(1.0, max(0.0, score)), 4)
    state.confidence = ConfidenceResult(score=score, label=_label_for(score))
    return state

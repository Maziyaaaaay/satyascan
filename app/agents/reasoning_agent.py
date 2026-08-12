from pydantic import BaseModel

from app.agents._call_logging import llm_provider_name
from app.agents.prompts import load as load_prompt
from app.agents.state import PipelineState, ProviderCallRecord, ReasoningResult
from app.models.enums import Verdict
from app.providers.bundle import Providers

SYSTEM_PROMPT = load_prompt("reasoning_agent")


class _ReasoningSchema(BaseModel):
    verdict: Verdict
    rationale: str
    certainty: float = 0.5


def _build_user_prompt(state: PipelineState) -> str:
    claim_text = state.claims[0].normalized_text if state.claims else (state.input_text or "(no text claim - image only)")
    if state.ranked_evidence:
        evidence_lines = "\n".join(
            f"- [{e.stance.value}] {e.claim_snippet} (source: {e.source_domain or 'unknown'}, "
            f"relevance={e.relevance_score})"
            for e in state.ranked_evidence
        )
    else:
        evidence_lines = "No evidence was found."
    return f"Claim: {claim_text}\n\nEvidence:\n{evidence_lines}"


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    response = await providers.llm.generate(
        system_prompt=SYSTEM_PROMPT, user_prompt=_build_user_prompt(state), response_schema=_ReasoningSchema
    )
    state.provider_calls.append(
        ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:reasoning_agent")
    )
    parsed = _ReasoningSchema.model_validate(response.parsed)
    certainty = min(1.0, max(0.0, parsed.certainty))
    state.reasoning = ReasoningResult(verdict=parsed.verdict, rationale=parsed.rationale, certainty=certainty)
    return state

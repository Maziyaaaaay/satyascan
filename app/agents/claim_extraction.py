from typing import List

from pydantic import BaseModel, Field

from app.agents._call_logging import llm_provider_name
from app.agents.prompts import load as load_prompt
from app.agents.state import ExtractedClaim, PipelineState, ProviderCallRecord
from app.providers.bundle import Providers

SYSTEM_PROMPT = load_prompt("claim_extraction")


class _ExtractionSchema(BaseModel):
    claims: List[str] = Field(default_factory=list)


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    text = state.input_text or ""
    response = await providers.llm.generate(
        system_prompt=SYSTEM_PROMPT, user_prompt=text, response_schema=_ExtractionSchema
    )
    state.provider_calls.append(
        ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:claim_extraction")
    )
    parsed = _ExtractionSchema.model_validate(response.parsed)
    claims = parsed.claims or [text]
    state.claims = [ExtractedClaim(text=text, normalized_text=c) for c in claims if c]
    return state

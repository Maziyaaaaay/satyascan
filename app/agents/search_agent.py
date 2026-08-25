from pydantic import BaseModel

from app.agents._call_logging import llm_provider_name
from app.agents.prompts import load as load_prompt
from app.agents.state import PipelineState, ProviderCallRecord, SearchResult
from app.models.enums import ProviderName
from app.providers.base import FactCheckResult
from app.providers.bundle import Providers

MAX_CLAIMS_SEARCHED = 3

_STANCE_SYSTEM_PROMPT = load_prompt("web_search_stance")
_STANCE_TO_RATING = {"supports": "True", "contradicts": "False"}


class _StanceSchema(BaseModel):
    stance: str


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    claims = state.claims[:MAX_CLAIMS_SEARCHED] or []
    fact_checks = []
    for claim in claims:
        results = await providers.fact_check.search_claims(claim.normalized_text)
        state.provider_calls.append(
            ProviderCallRecord(provider=ProviderName.google_fact_check, endpoint="search_claims")
        )
        fact_checks.extend(results)

    if claims:
        # Always run a live web search alongside the fact-check lookup,
        # not only when fact_checks is empty - confirmed live that the
        # Fact Check Tools API can return *non-empty but off-topic*
        # results (e.g. old fact-checks about a fake video "of CM Vijay",
        # which mention him as CM only in passing) that a reasoning LLM
        # then misreads as debunking the actual claim. Live search gives
        # on-topic, current evidence regardless of what that keyword
        # search happens to surface. (Deliberately NOT using an LLM's own
        # built-in search tool for this - confirmed live that it still
        # overrides fresh results with its own stale prior on a real case.)
        web_result = await providers.web_search.search(claims[0].normalized_text)
        if web_result is not None:
            state.provider_calls.append(ProviderCallRecord(provider=ProviderName.serper, endpoint="search"))
            rating = await _classify_stance(providers, claims[0].normalized_text, web_result.summary, state)
            fact_checks.append(
                FactCheckResult(
                    claim_text=web_result.summary,
                    rating=rating,
                    publisher="Live web search",
                    url=web_result.source_urls[0] if web_result.source_urls else None,
                    review_date=None,
                )
            )

    state.search = SearchResult(fact_checks=fact_checks)
    return state


async def _classify_stance(providers: Providers, claim_text: str, web_summary: str, state: PipelineState):
    """Determines whether the live search result actually supports or
    contradicts the claim, so it gets tagged with a real stance instead of
    always "neutral" - a search result left neutral is invisible to
    confidence_scoring's stance tally even when it's the exact evidence
    that decided the verdict, which was confirmed live to silently cap
    confidence at ~medium on an otherwise well-supported true verdict.
    Best-effort: any failure here just means "no rating", not a crash."""
    try:
        response = await providers.llm.generate(
            system_prompt=_STANCE_SYSTEM_PROMPT,
            user_prompt=f"Claim: {claim_text}\n\nWeb search summary:\n{web_summary}",
            response_schema=_StanceSchema,
        )
        state.provider_calls.append(
            ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:web_search_stance")
        )
        parsed = _StanceSchema.model_validate(response.parsed)
        return _STANCE_TO_RATING.get(parsed.stance.strip().lower())
    except Exception:
        return None

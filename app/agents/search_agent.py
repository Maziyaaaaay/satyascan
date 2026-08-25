from app.agents.state import PipelineState, ProviderCallRecord, SearchResult
from app.models.enums import ProviderName
from app.providers.base import FactCheckResult
from app.providers.bundle import Providers

MAX_CLAIMS_SEARCHED = 3


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    claims = state.claims[:MAX_CLAIMS_SEARCHED] or []
    fact_checks = []
    for claim in claims:
        results = await providers.fact_check.search_claims(claim.normalized_text)
        state.provider_calls.append(
            ProviderCallRecord(provider=ProviderName.google_fact_check, endpoint="search_claims")
        )
        fact_checks.extend(results)

    if not fact_checks and claims:
        # No existing fact-check article covers this claim - likely either
        # very recent (nothing published on it yet) or too obscure. Fall
        # back to live web-search grounding so the verdict isn't decided
        # purely on the reasoning LLM's frozen training-time knowledge.
        grounded = await providers.llm.search_grounded(claims[0].normalized_text)
        if grounded is not None:
            state.provider_calls.append(ProviderCallRecord(provider=ProviderName.gemini, endpoint="search_grounded"))
            fact_checks.append(
                FactCheckResult(
                    claim_text=grounded.summary,
                    rating=None,
                    publisher="Live web search",
                    url=grounded.source_urls[0] if grounded.source_urls else None,
                    review_date=None,
                )
            )

    state.search = SearchResult(fact_checks=fact_checks)
    return state

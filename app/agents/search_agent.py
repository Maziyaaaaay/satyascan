from app.agents.state import PipelineState, ProviderCallRecord, SearchResult
from app.models.enums import ProviderName
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
    state.search = SearchResult(fact_checks=fact_checks)
    return state

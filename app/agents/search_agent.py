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

_OFFICEHOLDER_SYSTEM_PROMPT = load_prompt("officeholder_query")


class _StanceSchema(BaseModel):
    stance: str


class _OfficeholderQuerySchema(BaseModel):
    query: str


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
        search_query = claims[0].normalized_text
        officeholder_query = await _officeholder_search_query(providers, search_query, state)
        if officeholder_query:
            # A claim like "X is the current <role>" searched verbatim
            # tends to surface X's own biography page, whose summary can
            # bury or contradict itself about whether X still holds the
            # role today (e.g. one line says "is the current..." while
            # another says "served ... to [an end date]" - both about the
            # same stale page). Searching the role generically instead
            # ("who is the current <role>") surfaces a direct, current
            # answer instead. Confirmed live on a real case: the verbatim
            # claim query gave a garbled, self-contradicting summary the
            # reasoning LLM misread as confirming a person who had
            # actually since been replaced; the generic role query gave a
            # clean, unambiguous, correct answer.
            search_query = officeholder_query

        web_result = await providers.web_search.search(search_query)
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


async def _officeholder_search_query(providers: Providers, claim_text: str, state: PipelineState):
    """Returns a generic "who currently holds <role>" search query if the
    claim asserts a specific person currently holds a position/title/role,
    else None. Best-effort: any failure just means "search the claim
    verbatim, as before" - never a crash."""
    try:
        response = await providers.llm.generate(
            system_prompt=_OFFICEHOLDER_SYSTEM_PROMPT,
            user_prompt=f"Claim: {claim_text}",
            response_schema=_OfficeholderQuerySchema,
            # This is a narrow classification, not creative writing - low
            # temperature so the same claim reliably gets reformulated the
            # same way every time, rather than only sometimes.
            temperature=0.0,
        )
        state.provider_calls.append(
            ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:officeholder_query")
        )
        parsed = _OfficeholderQuerySchema.model_validate(response.parsed)
        return parsed.query.strip() or None
    except Exception:
        return None


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
            # Same reasoning as _officeholder_search_query: a narrow
            # classification, not creative writing - confirmed live that
            # the default temperature let the exact same claim flip
            # between "supports" and a more cautious read from one call to
            # the next, which is what let a wrong, overconfident verdict
            # through some of the time even after the query-reformulation
            # fix (evidence itself can still be genuinely ambiguous, but
            # this removes classification-noise as a separate source of
            # inconsistency on top of that).
            temperature=0.0,
        )
        state.provider_calls.append(
            ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:web_search_stance")
        )
        parsed = _StanceSchema.model_validate(response.parsed)
        return _STANCE_TO_RATING.get(parsed.stance.strip().lower())
    except Exception:
        return None

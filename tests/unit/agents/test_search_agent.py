import dataclasses
from typing import List, Optional

import pytest

from app.agents import search_agent
from app.agents.state import ExtractedClaim
from app.providers.base import FactCheckProvider, FactCheckResult, LLMProvider, LLMResponse, WebSearchProvider, WebSearchResult


class _EmptyFactCheckProvider(FactCheckProvider):
    async def search_claims(self, query: str, language_code: str = "en") -> List[FactCheckResult]:
        return []


class _WorkingWebSearchProvider(WebSearchProvider):
    async def search(self, query: str) -> Optional[WebSearchResult]:
        return WebSearchResult(summary="Live search says X.", source_urls=["https://example.com/live"])


class _FailingWebSearchProvider(WebSearchProvider):
    async def search(self, query: str) -> Optional[WebSearchResult]:
        return None


class _RecordingWebSearchProvider(WebSearchProvider):
    """Records every query it's asked to search, for asserting on exactly
    what search_agent chose to search for."""

    def __init__(self) -> None:
        self.queries: List[str] = []

    async def search(self, query: str) -> Optional[WebSearchResult]:
        self.queries.append(query)
        return WebSearchResult(summary="some result", source_urls=["https://example.com/x"])


class _ScriptedLLMProvider(LLMProvider):
    """Returns a fixed, hand-written response regardless of prompt - used
    to test the officeholder-query reformulation deterministically, since
    the generic MockLLMProvider's schema-filling always returns a non-empty
    string for any str field and can't represent "not an officeholder
    claim" (an empty string)."""

    def __init__(self, response: dict):
        self._response = response

    async def generate(self, *, system_prompt, user_prompt, response_schema=None, temperature=0.2):
        return LLMResponse(text="", parsed=self._response, model="scripted", is_mock=True)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] for _ in texts]


@pytest.mark.asyncio
async def test_search_returns_fact_checks_for_claims(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="drinking hot water cures COVID")]
    result = await search_agent.run(base_state, providers)
    assert result.search is not None
    assert len(result.search.fact_checks) >= 1


@pytest.mark.asyncio
async def test_no_claims_returns_empty_search_result(base_state, providers):
    result = await search_agent.run(base_state, providers)
    assert result.search.fact_checks == []


@pytest.mark.asyncio
async def test_falls_back_to_web_search_when_no_fact_checks_found(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="some very recent claim")]
    providers = dataclasses.replace(
        providers, fact_check=_EmptyFactCheckProvider(), web_search=_WorkingWebSearchProvider()
    )

    result = await search_agent.run(base_state, providers)

    assert len(result.search.fact_checks) == 1
    assert result.search.fact_checks[0].claim_text == "Live search says X."
    assert result.search.fact_checks[0].publisher == "Live web search"
    assert result.search.fact_checks[0].url == "https://example.com/live"


@pytest.mark.asyncio
async def test_stays_empty_when_web_search_unavailable(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="some very recent claim")]
    providers = dataclasses.replace(
        providers, fact_check=_EmptyFactCheckProvider(), web_search=_FailingWebSearchProvider()
    )

    result = await search_agent.run(base_state, providers)

    assert result.search.fact_checks == []


@pytest.mark.asyncio
async def test_officeholder_claim_reformulates_to_generic_role_query(base_state, providers):
    # Regression test for a real, reproduced bug: searching "X is the
    # current <role>" verbatim can surface X's own (possibly stale)
    # biography page, whose summary can bury or contradict itself about
    # whether X still holds the role - confirmed live that this made the
    # bot confidently confirm someone who had actually since been
    # replaced. Searching the role generically instead ("who is the
    # current <role>") reliably surfaced the correct, current answer.
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="Pinarayi Vijayan is the Chief Minister of Kerala")]
    recording_search = _RecordingWebSearchProvider()
    providers = dataclasses.replace(
        providers,
        fact_check=_EmptyFactCheckProvider(),
        web_search=recording_search,
        llm=_ScriptedLLMProvider({"query": "current chief minister of Kerala"}),
    )

    await search_agent.run(base_state, providers)

    assert recording_search.queries == ["current chief minister of Kerala"]


@pytest.mark.asyncio
async def test_non_officeholder_claim_searches_the_claim_verbatim(base_state, providers):
    base_state.claims = [ExtractedClaim(text="orig", normalized_text="Drinking hot water cures COVID")]
    recording_search = _RecordingWebSearchProvider()
    providers = dataclasses.replace(
        providers,
        fact_check=_EmptyFactCheckProvider(),
        web_search=recording_search,
        llm=_ScriptedLLMProvider({"query": ""}),
    )

    await search_agent.run(base_state, providers)

    assert recording_search.queries == ["Drinking hot water cures COVID"]

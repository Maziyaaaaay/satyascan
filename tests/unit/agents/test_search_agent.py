import dataclasses
from typing import List, Optional

import pytest

from app.agents import search_agent
from app.agents.state import ExtractedClaim
from app.providers.base import FactCheckProvider, FactCheckResult, WebSearchProvider, WebSearchResult


class _EmptyFactCheckProvider(FactCheckProvider):
    async def search_claims(self, query: str, language_code: str = "en") -> List[FactCheckResult]:
        return []


class _WorkingWebSearchProvider(WebSearchProvider):
    async def search(self, query: str) -> Optional[WebSearchResult]:
        return WebSearchResult(summary="Live search says X.", source_urls=["https://example.com/live"])


class _FailingWebSearchProvider(WebSearchProvider):
    async def search(self, query: str) -> Optional[WebSearchResult]:
        return None


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

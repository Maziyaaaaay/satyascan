import hashlib
from typing import Optional

from app.providers.base import WebSearchProvider, WebSearchResult


class MockWebSearchProvider(WebSearchProvider):
    """Deterministic stand-in for a real web-search API. Derived from a
    hash of the query, not any actual search - for pipeline/UI testing
    only."""

    async def search(self, query: str) -> Optional[WebSearchResult]:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return WebSearchResult(
            summary=f"Mock live-search result for: {query}",
            source_urls=[f"https://example.com/mock-search/{digest[:8]}"],
        )

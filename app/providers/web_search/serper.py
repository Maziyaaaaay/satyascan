from typing import Optional

import httpx

from app.providers.base import WebSearchProvider, WebSearchResult

SERPER_URL = "https://google.serper.dev/search"
MAX_ORGANIC_RESULTS = 5


class SerperWebSearchProvider(WebSearchProvider):
    """Real Google Search results via serper.dev - an independent search
    index, not an LLM's own (unreliable) built-in search tool."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str) -> Optional[WebSearchResult]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    SERPER_URL,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                    json={"q": query},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            # Best-effort fallback: a Serper outage/quota issue must degrade
            # to "no live-search evidence available", not break the pipeline.
            return None

        source_urls = []
        summary_parts = []

        answer_box = data.get("answerBox")
        if answer_box and answer_box.get("snippet"):
            summary_parts.append(answer_box["snippet"])
            if answer_box.get("link"):
                source_urls.append(answer_box["link"])

        for result in data.get("organic", [])[:MAX_ORGANIC_RESULTS]:
            snippet = result.get("snippet")
            link = result.get("link")
            date = result.get("date")
            if snippet:
                summary_parts.append(f"{snippet}" + (f" ({date})" if date else ""))
            if link:
                source_urls.append(link)

        if not summary_parts:
            return None

        return WebSearchResult(summary="\n".join(summary_parts), source_urls=source_urls)

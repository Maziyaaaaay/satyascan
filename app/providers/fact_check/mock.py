import hashlib
from typing import List

from app.providers.base import FactCheckProvider, FactCheckResult

_PUBLISHERS = ["Boom Live", "Alt News", "PolitiFact", "Full Fact", "AFP Fact Check"]
_RATINGS = ["False", "Misleading", "Partly False", "True", "Unproven"]


class MockFactCheckProvider(FactCheckProvider):
    """Deterministic stand-in for the Google Fact Check Tools API. Always
    returns at least one result so downstream evidence-ranking/reasoning
    logic has something to work with in tests."""

    async def search_claims(self, query: str, language_code: str = "en") -> List[FactCheckResult]:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        n = int(digest[:8], 16)
        count = 1 + (n % 3)
        results = []
        for i in range(count):
            m = int(hashlib.sha256(f"{query}:{i}".encode("utf-8")).hexdigest()[:8], 16)
            results.append(
                FactCheckResult(
                    claim_text=query,
                    rating=_RATINGS[m % len(_RATINGS)],
                    publisher=_PUBLISHERS[m % len(_PUBLISHERS)],
                    url=f"https://example-factcheck.org/claim/{m % 100000:x}",
                    review_date="2025-01-01",
                )
            )
        return results

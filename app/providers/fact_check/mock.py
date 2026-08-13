import hashlib
from typing import List

from app.providers.base import FactCheckProvider, FactCheckResult

_PUBLISHERS = [
    ("Boom Live", "boomlive.in"),
    ("Alt News", "altnews.in"),
    ("PolitiFact", "politifact.com"),
    ("Full Fact", "fullfact.org"),
    ("AFP Fact Check", "factcheck.afp.com"),
]
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
            publisher, domain = _PUBLISHERS[m % len(_PUBLISHERS)]
            results.append(
                FactCheckResult(
                    claim_text=query,
                    rating=_RATINGS[m % len(_RATINGS)],
                    publisher=publisher,
                    url=f"https://{domain}/claim/{m % 100000:x}",
                    review_date="2025-01-01",
                )
            )
        return results

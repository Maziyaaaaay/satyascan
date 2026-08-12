from typing import List

import httpx

from app.providers.base import FactCheckProvider, FactCheckResult

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckProvider(FactCheckProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search_claims(self, query: str, language_code: str = "en") -> List[FactCheckResult]:
        params = {"query": query, "languageCode": language_code, "key": self._api_key}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for claim in data.get("claims", []):
            for review in claim.get("claimReview", []) or [{}]:
                results.append(
                    FactCheckResult(
                        claim_text=claim.get("text", query),
                        rating=review.get("textualRating"),
                        publisher=(review.get("publisher") or {}).get("name"),
                        url=review.get("url"),
                        review_date=review.get("reviewDate"),
                    )
                )
        return results

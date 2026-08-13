import hashlib
from typing import List

from app.providers.base import ImageSearchProvider, OCRResult, ReverseImageMatch

_MOCK_NEWS_DOMAINS = ["timesnow.example", "dailychronicle.example", "regionalnews.example"]


class MockImageSearchProvider(ImageSearchProvider):
    """Deterministic stand-in for Google Cloud Vision (web detection + text
    detection), keyed off a hash of the image bytes rather than any real
    visual analysis."""

    async def reverse_image_search(self, image_bytes: bytes) -> List[ReverseImageMatch]:
        digest = hashlib.sha256(image_bytes).hexdigest()
        n = int(digest[:8], 16)
        count = n % 3
        return [
            ReverseImageMatch(
                url=f"https://{_MOCK_NEWS_DOMAINS[i % len(_MOCK_NEWS_DOMAINS)]}/article/{digest[i:i + 6]}",
                page_title=f"mock matching page {i + 1}",
                match_confidence=round(0.5 + (i * 0.1), 2),
            )
            for i in range(count)
        ]

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        digest = hashlib.sha256(image_bytes).hexdigest()
        return OCRResult(text=f"[mock OCR text {digest[:8]}]", language_code="en")

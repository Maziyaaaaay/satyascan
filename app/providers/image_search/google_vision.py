from typing import List

from app.providers.base import ImageSearchProvider, OCRResult, ReverseImageMatch


class GoogleVisionImageSearchProvider(ImageSearchProvider):
    """Real reverse image search (web detection) + OCR (text detection) via
    Google Cloud Vision. Requires GOOGLE_APPLICATION_CREDENTIALS (a service
    account JSON path) rather than a simple API key, per Vision's auth model;
    GOOGLE_CLOUD_VISION_API_KEY still gates whether this class is selected."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def _client(self):
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-vision is not installed. Install with: pip install -e '.[real]'"
            ) from exc
        return vision.ImageAnnotatorClient(client_options={"api_key": self._api_key})

    async def reverse_image_search(self, image_bytes: bytes) -> List[ReverseImageMatch]:
        import asyncio

        def _call():
            from google.cloud import vision

            client = self._client()
            image = vision.Image(content=image_bytes)
            response = client.web_detection(image=image)
            matches = []
            for page in response.web_detection.pages_with_matching_images:
                matches.append(
                    ReverseImageMatch(
                        url=page.url,
                        page_title=page.page_title or None,
                        match_confidence=1.0,
                    )
                )
            return matches

        return await asyncio.to_thread(_call)

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        import asyncio

        def _call():
            from google.cloud import vision

            client = self._client()
            image = vision.Image(content=image_bytes)
            response = client.text_detection(image=image)
            text = response.full_text_annotation.text if response.full_text_annotation else ""
            return OCRResult(text=text)

        return await asyncio.to_thread(_call)

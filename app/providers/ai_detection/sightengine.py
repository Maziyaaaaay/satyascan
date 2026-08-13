import httpx

from app.providers.base import AIDetectionResult, AIImageDetectionProvider

API_URL = "https://api.sightengine.com/1.0/check.json"
LIKELY_THRESHOLD = 0.5


class SightengineAIDetectionProvider(AIImageDetectionProvider):
    """Real adapter for Sightengine's 'genai' (AI-generated image) detection
    model. NOTE: built against Sightengine's documented API shape but never
    exercised against a live account (no credentials were available during
    development) - verify the response field path (`type.ai_generated`)
    against Sightengine's current docs once you have an API user/secret; see
    NEXT_STEPS.md.
    """

    def __init__(self, api_user: str, api_secret: str):
        self._api_user = api_user
        self._api_secret = api_secret

    async def detect(self, image_bytes: bytes) -> AIDetectionResult:
        params = {"models": "genai", "api_user": self._api_user, "api_secret": self._api_secret}
        files = {"media": ("image", image_bytes)}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(API_URL, params=params, files=files)
            response.raise_for_status()
            data = response.json()

        probability = float(data.get("type", {}).get("ai_generated", 0.0))
        return AIDetectionResult(
            ai_generated_probability=probability,
            is_likely_ai_generated=probability >= LIKELY_THRESHOLD,
            reasoning=f"Sightengine genai model score: {probability:.2f}",
        )

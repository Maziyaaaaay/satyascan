import hashlib

from app.providers.base import AIDetectionResult, AIImageDetectionProvider

_LIKELY_AI_REASON_BANK = [
    "The image shows telltale synthesis artifacts around fine detail (hands, "
    "text, and edges) commonly seen in AI-generated images.",
    "Lighting and texture patterns are unnaturally uniform in a way typical of "
    "diffusion-model output rather than a real photograph.",
    "Background elements show the kind of incoherent repetition often produced "
    "by generative image models.",
]
_LIKELY_REAL_REASON_BANK = [
    "No strong synthesis artifacts were detected - noise patterns and edge "
    "detail are consistent with a real photograph.",
    "Lighting, shadows, and texture are consistent with a genuine camera "
    "capture rather than generated content.",
    "The image's compression and sensor-noise signature matches typical "
    "camera output rather than a generative model's fingerprint.",
]


class MockAIImageDetectionProvider(AIImageDetectionProvider):
    """Deterministic stand-in for a real AI-generated-image detector (e.g.
    Sightengine's genai model). The probability and reasoning are derived
    from a hash of the image bytes, not any actual visual analysis - this is
    for UI/pipeline testing only, never treat it as a real signal."""

    async def detect(self, image_bytes: bytes) -> AIDetectionResult:
        digest = hashlib.sha256(image_bytes).hexdigest()
        n = int(digest[:8], 16)
        probability = round((n % 1000) / 1000, 4)
        is_likely = probability >= 0.5

        bank = _LIKELY_AI_REASON_BANK if is_likely else _LIKELY_REAL_REASON_BANK
        reasoning = bank[n % len(bank)]

        return AIDetectionResult(
            ai_generated_probability=probability, is_likely_ai_generated=is_likely, reasoning=reasoning
        )

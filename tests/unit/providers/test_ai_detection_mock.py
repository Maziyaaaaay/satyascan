import pytest

from app.providers.ai_detection.mock import MockAIImageDetectionProvider
from app.providers.base import AIImageDetectionProvider


@pytest.mark.asyncio
async def test_mock_ai_detection_is_an_ai_image_detection_provider():
    assert isinstance(MockAIImageDetectionProvider(), AIImageDetectionProvider)


@pytest.mark.asyncio
async def test_detect_is_deterministic():
    provider = MockAIImageDetectionProvider()
    r1 = await provider.detect(b"some-image-bytes")
    r2 = await provider.detect(b"some-image-bytes")
    assert r1.model_dump() == r2.model_dump()


@pytest.mark.asyncio
async def test_detect_returns_bounded_probability_and_consistent_flag():
    provider = MockAIImageDetectionProvider()
    result = await provider.detect(b"another-image")
    assert 0.0 <= result.ai_generated_probability <= 1.0
    assert result.is_likely_ai_generated == (result.ai_generated_probability >= 0.5)
    assert result.reasoning

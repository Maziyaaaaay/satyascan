import pytest

from app.providers.base import ImageSearchProvider
from app.providers.image_search.mock import MockImageSearchProvider

_FAKE_IMAGE_BYTES = b"not-a-real-image-but-good-enough-for-hashing"


@pytest.mark.asyncio
async def test_mock_image_search_is_an_image_search_provider():
    assert isinstance(MockImageSearchProvider(), ImageSearchProvider)


@pytest.mark.asyncio
async def test_reverse_image_search_is_deterministic():
    provider = MockImageSearchProvider()
    m1 = await provider.reverse_image_search(_FAKE_IMAGE_BYTES)
    m2 = await provider.reverse_image_search(_FAKE_IMAGE_BYTES)
    assert [m.model_dump() for m in m1] == [m.model_dump() for m in m2]


@pytest.mark.asyncio
async def test_extract_text_always_returns_nonempty_text():
    provider = MockImageSearchProvider()
    result = await provider.extract_text(_FAKE_IMAGE_BYTES)
    assert result.text
    assert result.language_code == "en"

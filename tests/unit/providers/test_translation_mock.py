import pytest

from app.providers.base import TranslationProvider
from app.providers.translation.mock import MockTranslationProvider


@pytest.mark.asyncio
async def test_mock_translation_is_a_translation_provider():
    assert isinstance(MockTranslationProvider(), TranslationProvider)


@pytest.mark.asyncio
async def test_translate_to_malayalam_returns_malayalam_text():
    provider = MockTranslationProvider()
    text = await provider.translate("This claim is false.", target_language="ml")
    assert any("ഀ" <= ch <= "ൿ" for ch in text)


@pytest.mark.asyncio
async def test_detect_language_distinguishes_malayalam_from_english():
    provider = MockTranslationProvider()
    assert await provider.detect_language("This is English text.") == "en"
    assert await provider.detect_language("ഇത് മലയാളമാണ്") == "ml"

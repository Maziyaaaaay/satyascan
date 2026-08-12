from typing import Optional

from app.providers.base import TranslationProvider

_MOCK_TRANSLATIONS = {
    "ml": "ഇത് ഒരു മോക്ക് മലയാളം വിശദീകരണമാണ്.",
    "en": "[mock English translation]",
}


class MockTranslationProvider(TranslationProvider):
    async def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        return _MOCK_TRANSLATIONS.get(target_language, f"[mock translation to {target_language}] {text}")

    async def detect_language(self, text: str) -> str:
        has_malayalam = any("ഀ" <= ch <= "ൿ" for ch in text)
        return "ml" if has_malayalam else "en"

from typing import Optional

from app.providers.base import TranslationProvider

_MOCK_TRANSLATIONS = {
    "ml": "ഇത് ഒരു മോക്ക് മലയാളം വിശദീകരണമാണ്.",
    "hi": "यह एक मॉक हिंदी व्याख्या है।",
    "ta": "இது ஒரு போலி தமிழ் விளக்கமாகும்.",
    "en": "[mock English translation]",
}

# (start, end) Unicode ranges used to guess a script for the mock's
# detect_language - real detection is Google Translate's job; this only
# needs to be good enough for deterministic pipeline/UI tests.
_SCRIPT_RANGES = {
    "ml": ("ഀ", "ൿ"),  # Malayalam
    "hi": ("ऀ", "ॿ"),  # Devanagari
    "ta": ("஀", "௿"),  # Tamil
}


class MockTranslationProvider(TranslationProvider):
    async def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        return _MOCK_TRANSLATIONS.get(target_language, f"[mock translation to {target_language}] {text}")

    async def detect_language(self, text: str) -> str:
        for code, (start, end) in _SCRIPT_RANGES.items():
            if any(start <= ch <= end for ch in text):
                return code
        return "en"

from typing import Optional

from app.providers.base import TranslationProvider


class GoogleTranslateProvider(TranslationProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    def _client(self):
        try:
            from google.cloud import translate_v2 as translate
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-translate is not installed. Install with: pip install -e '.[real]'"
            ) from exc
        return translate.Client(client_options={"api_key": self._api_key})

    async def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        import asyncio

        def _call():
            client = self._client()
            result = client.translate(text, target_language=target_language, source_language=source_language)
            return result["translatedText"]

        return await asyncio.to_thread(_call)

    async def detect_language(self, text: str) -> str:
        import asyncio

        def _call():
            client = self._client()
            result = client.detect_language(text)
            return result["language"]

        return await asyncio.to_thread(_call)

from typing import Optional

import httpx

from app.providers.base import TranslationProvider

# Calling the Translation API v2 REST endpoint directly rather than via the
# google-cloud-translate SDK client: that client insists on Application
# Default Credentials (a service account) even when given client_options with
# an api_key, and errors with DefaultCredentialsError - confirmed against a
# live key. The bare REST endpoint accepts a plain API key as documented.
API_URL = "https://translation.googleapis.com/language/translate/v2"
DETECT_URL = f"{API_URL}/detect"


class GoogleTranslateProvider(TranslationProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        params = {"key": self._api_key, "q": text, "target": target_language, "format": "text"}
        if source_language:
            params["source"] = source_language

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        return data["data"]["translations"][0]["translatedText"]

    async def detect_language(self, text: str) -> str:
        params = {"key": self._api_key, "q": text}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(DETECT_URL, params=params)
            response.raise_for_status()
            data = response.json()

        return data["data"]["detections"][0][0]["language"]

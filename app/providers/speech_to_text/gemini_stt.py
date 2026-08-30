import base64
from typing import Optional

import httpx

from app.providers.base import SpeechToTextProvider

MODEL = "gemini-flash-lite-latest"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

_TRANSCRIBE_PROMPT = (
    "Transcribe the speech in this audio exactly as spoken, in its original "
    "language and script. Output only the transcript text - no commentary, "
    "no translation, no quotation marks, no summary."
)


class GeminiSpeechToTextProvider(SpeechToTextProvider):
    """Uses Gemini's native audio understanding instead of a dedicated
    speech-to-text API - confirmed live that gemini-flash-lite-latest
    transcribes a WhatsApp-style voice note (OGG/Opus) accurately in ~2s.
    Chosen over OpenAIWhisperProvider specifically because it reuses the
    same GEMINI_API_KEY already required for the rest of the pipeline,
    rather than needing a separate OpenAI billing setup - Whisper was
    previously blocked for months on an OpenAI account with
    insufficient_quota (see PROJECT_STATUS.md), which this sidesteps
    entirely rather than fixes.

    Uses the raw REST endpoint (not the google-generativeai SDK), matching
    the pattern GoogleTranslateProvider already uses in this codebase -
    simpler than fighting the SDK's blob/Part conversion for inline audio
    data, and already confirmed working against a live key."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def transcribe(self, audio_bytes: bytes, mime_type: Optional[str] = None) -> str:
        # WhatsApp voice notes and forwarded audio both arrive as audio/ogg
        # (opus codec) - Gemini accepts that mime type directly, no
        # re-encoding or filename-extension trick needed (contrast with
        # OpenAIWhisperProvider, which had to fake one).
        audio_mime = mime_type or "audio/ogg"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _TRANSCRIBE_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": audio_mime,
                                "data": base64.b64encode(audio_bytes).decode(),
                            }
                        },
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, params={"key": self._api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            # Gemini can return a candidate with no text part (e.g. blocked
            # by a safety filter, or silent/unintelligible audio) - treat
            # that as "nothing transcribed" rather than raise, so the
            # caller falls through to its existing "no claim found" path.
            return ""

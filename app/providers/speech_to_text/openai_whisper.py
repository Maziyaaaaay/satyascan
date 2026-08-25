import io
from typing import Optional

from app.providers.base import SpeechToTextProvider

DEFAULT_MODEL = "whisper-1"


class OpenAIWhisperProvider(SpeechToTextProvider):
    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL):
        self._api_key = api_key
        self._model_name = model_name

    def _client(self):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed. Install with: pip install -e '.[real]'") from exc
        return AsyncOpenAI(api_key=self._api_key)

    async def transcribe(self, audio_bytes: bytes, mime_type: Optional[str] = None) -> str:
        client = self._client()
        # WhatsApp voice notes arrive as audio/ogg (opus codec); Whisper's
        # API infers format from the filename extension, not the mime type
        # we pass around internally, so give it a plausible one.
        extension = "ogg" if mime_type is None or "ogg" in mime_type else mime_type.split("/")[-1]
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"voice_note.{extension}"
        transcript = await client.audio.transcriptions.create(model=self._model_name, file=audio_file)
        return transcript.text

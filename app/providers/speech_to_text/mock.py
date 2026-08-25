import hashlib
from typing import Optional

from app.providers.base import SpeechToTextProvider

_TRANSCRIPT_BANK = [
    "Drinking hot water cures COVID-19.",
    "The new policy takes effect starting next month.",
    "This photo shows the event that happened yesterday.",
    "Scientists confirmed the discovery earlier this week.",
]


class MockSpeechToTextProvider(SpeechToTextProvider):
    """Deterministic stand-in for a real speech-to-text service. The
    returned transcript is derived from a hash of the audio bytes, not any
    actual audio analysis - for pipeline/UI testing only."""

    async def transcribe(self, audio_bytes: bytes, mime_type: Optional[str] = None) -> str:
        digest = hashlib.sha256(audio_bytes).hexdigest()
        n = int(digest[:8], 16)
        return _TRANSCRIPT_BANK[n % len(_TRANSCRIPT_BANK)]

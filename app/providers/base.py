from abc import ABC, abstractmethod
from typing import List, Optional, Type

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    text: str
    parsed: Optional[dict] = None
    model: str
    is_mock: bool = False


class FactCheckResult(BaseModel):
    claim_text: str
    rating: Optional[str] = None
    publisher: Optional[str] = None
    url: Optional[str] = None
    review_date: Optional[str] = None


class ReverseImageMatch(BaseModel):
    url: str
    page_title: Optional[str] = None
    match_confidence: float = 0.0


class OCRResult(BaseModel):
    text: str
    language_code: Optional[str] = None


class AIDetectionResult(BaseModel):
    ai_generated_probability: float
    is_likely_ai_generated: bool
    reasoning: str


class WebSearchResult(BaseModel):
    summary: str
    source_urls: List[str] = Field(default_factory=list)


class LLMProvider(ABC):
    """Text generation + embeddings. When response_schema is given,
    implementations must return a LLMResponse whose `parsed` dict validates
    against that schema (real providers via structured-output/function
    calling; the mock via deterministic synthetic field values) so callers
    can treat mock and real identically."""

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse: ...

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]: ...


class FactCheckProvider(ABC):
    @abstractmethod
    async def search_claims(self, query: str, language_code: str = "en") -> List[FactCheckResult]: ...


class ImageSearchProvider(ABC):
    """Reverse image search + OCR, both backed by the same vendor (Google
    Cloud Vision) in the real implementation."""

    @abstractmethod
    async def reverse_image_search(self, image_bytes: bytes) -> List[ReverseImageMatch]: ...

    @abstractmethod
    async def extract_text(self, image_bytes: bytes) -> OCRResult: ...


class AIImageDetectionProvider(ABC):
    """Detects whether an image itself was AI-generated (deepfake/synthetic
    media) - distinct from ImageSearchProvider, which checks whether a real
    image is being recycled/used out of context. A separate capability from
    the original 8-agent PRD scope, added on request."""

    @abstractmethod
    async def detect(self, image_bytes: bytes) -> AIDetectionResult: ...


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str: ...

    @abstractmethod
    async def detect_language(self, text: str) -> str: ...


class WebSearchProvider(ABC):
    """Independent, real-time web search (not an LLM's own built-in search
    tool - confirmed live that Gemini's Google Search grounding still
    overrides fresh results with its own stale training-time belief on a
    real case, e.g. reporting a several-months-old change of government as
    "speculative or fictional"). Used as a fallback when no fact-check
    article covers a claim, so verdicts on recent events aren't decided by
    a model's frozen knowledge."""

    @abstractmethod
    async def search(self, query: str) -> Optional[WebSearchResult]: ...


class SpeechToTextProvider(ABC):
    """Transcribes a voice note / audio file to text so it can be run
    through the same claim-verification pipeline as a typed message."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, mime_type: Optional[str] = None) -> str: ...


class InteractiveButton(BaseModel):
    """One WhatsApp quick-reply button. WhatsApp caps titles at 20
    characters and a message at 3 buttons - callers should keep titles
    short (an emoji + a couple of words); real-provider implementations
    truncate defensively rather than reject a longer title outright."""

    id: str
    title: str


class WhatsAppClient(ABC):
    @abstractmethod
    async def send_text_message(self, to: str, body: str) -> str: ...

    @abstractmethod
    async def send_interactive_buttons(self, to: str, body: str, buttons: List[InteractiveButton]) -> str:
        """Send `body` with up to 3 native WhatsApp quick-reply buttons
        attached. The button click comes back on a later webhook as a
        message of type "interactive" with interactive.button_reply.id set
        to the id given here."""
        ...

    @abstractmethod
    async def download_media(self, media_id: str) -> bytes: ...

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> None: ...

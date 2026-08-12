from app.models.enums import ProviderName
from app.providers.base import LLMResponse


def llm_provider_name(response: LLMResponse) -> ProviderName:
    """Best-effort vendor tag from the model name string on the response -
    LLMResponse doesn't carry a ProviderName directly since a single
    LLMProvider instance (e.g. Gemini-with-OpenAI-fallback) can call either
    vendor per-request. Mock responses (model="mock-llm") default to the
    gemini label since the mock doesn't impersonate a specific vendor."""
    lowered = response.model.lower()
    if "gpt" in lowered or "openai" in lowered:
        return ProviderName.openai
    return ProviderName.gemini

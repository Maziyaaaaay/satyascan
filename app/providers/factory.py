from functools import lru_cache

from app.config import get_settings
from app.providers.base import (
    FactCheckProvider,
    ImageSearchProvider,
    LLMProvider,
    TranslationProvider,
    WhatsAppClient,
)


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.gemini_api_key:
        from app.providers.llm.gemini import GeminiProvider

        fallback = None
        if settings.openai_api_key:
            from app.providers.llm.openai_provider import OpenAIProvider

            fallback = OpenAIProvider(api_key=settings.openai_api_key)
        return GeminiProvider(api_key=settings.gemini_api_key, fallback=fallback)

    if settings.openai_api_key:
        from app.providers.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key)

    from app.providers.llm.mock import MockLLMProvider

    return MockLLMProvider()


@lru_cache
def get_fact_check_provider() -> FactCheckProvider:
    settings = get_settings()
    if settings.google_fact_check_api_key:
        from app.providers.fact_check.google_fact_check import GoogleFactCheckProvider

        return GoogleFactCheckProvider(api_key=settings.google_fact_check_api_key)

    from app.providers.fact_check.mock import MockFactCheckProvider

    return MockFactCheckProvider()


@lru_cache
def get_image_search_provider() -> ImageSearchProvider:
    settings = get_settings()
    if settings.google_cloud_vision_api_key:
        from app.providers.image_search.google_vision import GoogleVisionImageSearchProvider

        return GoogleVisionImageSearchProvider(api_key=settings.google_cloud_vision_api_key)

    from app.providers.image_search.mock import MockImageSearchProvider

    return MockImageSearchProvider()


@lru_cache
def get_translation_provider() -> TranslationProvider:
    settings = get_settings()
    if settings.google_translate_api_key:
        from app.providers.translation.google_translate import GoogleTranslateProvider

        return GoogleTranslateProvider(api_key=settings.google_translate_api_key)

    from app.providers.translation.mock import MockTranslationProvider

    return MockTranslationProvider()


@lru_cache
def get_whatsapp_client() -> WhatsAppClient:
    settings = get_settings()
    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        from app.providers.whatsapp.meta_cloud_api import MetaWhatsAppClient

        return MetaWhatsAppClient(
            access_token=settings.whatsapp_access_token,
            phone_number_id=settings.whatsapp_phone_number_id,
        )

    from app.providers.whatsapp.mock import MockWhatsAppClient

    return MockWhatsAppClient()


def reset_providers_for_tests() -> None:
    """Clear every provider factory's cache so a test that changes env vars
    (or wants a fresh Mock* instance) gets a clean slate."""
    get_llm_provider.cache_clear()
    get_fact_check_provider.cache_clear()
    get_image_search_provider.cache_clear()
    get_translation_provider.cache_clear()
    get_whatsapp_client.cache_clear()

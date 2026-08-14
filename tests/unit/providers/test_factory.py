import pytest

from app.config import get_settings
from app.providers.factory import (
    get_ai_detection_provider,
    get_fact_check_provider,
    get_image_search_provider,
    get_llm_provider,
    get_translation_provider,
    get_whatsapp_client,
    reset_providers_for_tests,
)
from app.providers.ai_detection.mock import MockAIImageDetectionProvider
from app.providers.fact_check.mock import MockFactCheckProvider
from app.providers.image_search.mock import MockImageSearchProvider
from app.providers.llm.mock import MockLLMProvider
from app.providers.translation.mock import MockTranslationProvider
from app.providers.whatsapp.mock import MockWhatsAppClient


@pytest.fixture(autouse=True)
def _clean_provider_state(monkeypatch):
    # Set to "" rather than delenv: pydantic-settings reads values straight
    # out of a real local .env file regardless of the OS environment, so
    # deleting an OS var doesn't hide a value already present in .env (which
    # may hold real keys for local dev). An OS env var explicitly set to ""
    # takes precedence over .env per pydantic-settings' source order, and ""
    # is falsy - the factory functions check truthiness, so this reliably
    # forces the mock path regardless of what's in .env.
    for var in [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_FACT_CHECK_API_KEY",
        "GOOGLE_CLOUD_VISION_API_KEY",
        "GOOGLE_TRANSLATE_API_KEY",
        "SIGHTENGINE_API_USER",
        "SIGHTENGINE_API_SECRET",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
    ]:
        monkeypatch.setenv(var, "")
    get_settings.cache_clear()
    reset_providers_for_tests()
    yield
    get_settings.cache_clear()
    reset_providers_for_tests()


def test_defaults_to_mocks_with_no_env_vars_set():
    assert isinstance(get_llm_provider(), MockLLMProvider)
    assert isinstance(get_fact_check_provider(), MockFactCheckProvider)
    assert isinstance(get_image_search_provider(), MockImageSearchProvider)
    assert isinstance(get_ai_detection_provider(), MockAIImageDetectionProvider)
    assert isinstance(get_translation_provider(), MockTranslationProvider)
    assert isinstance(get_whatsapp_client(), MockWhatsAppClient)


def test_sightengine_requires_both_user_and_secret(monkeypatch):
    monkeypatch.setenv("SIGHTENGINE_API_USER", "user-only")
    get_settings.cache_clear()
    reset_providers_for_tests()

    assert isinstance(get_ai_detection_provider(), MockAIImageDetectionProvider)


def test_sightengine_user_and_secret_selects_real_provider(monkeypatch):
    from app.providers.ai_detection.sightengine import SightengineAIDetectionProvider

    monkeypatch.setenv("SIGHTENGINE_API_USER", "user")
    monkeypatch.setenv("SIGHTENGINE_API_SECRET", "secret")
    get_settings.cache_clear()
    reset_providers_for_tests()

    assert isinstance(get_ai_detection_provider(), SightengineAIDetectionProvider)


def test_gemini_key_selects_real_gemini_provider(monkeypatch):
    from app.providers.llm.gemini import GeminiProvider

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    reset_providers_for_tests()

    assert isinstance(get_llm_provider(), GeminiProvider)


def test_openai_key_alone_selects_real_openai_provider(monkeypatch):
    from app.providers.llm.openai_provider import OpenAIProvider

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    reset_providers_for_tests()

    assert isinstance(get_llm_provider(), OpenAIProvider)


def test_whatsapp_requires_both_token_and_phone_id(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token-only")
    get_settings.cache_clear()
    reset_providers_for_tests()

    # Only one of the two required vars set - must still fall back to mock.
    assert isinstance(get_whatsapp_client(), MockWhatsAppClient)


def test_whatsapp_key_and_phone_id_selects_real_client(monkeypatch):
    from app.providers.whatsapp.meta_cloud_api import MetaWhatsAppClient

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    get_settings.cache_clear()
    reset_providers_for_tests()

    assert isinstance(get_whatsapp_client(), MetaWhatsAppClient)

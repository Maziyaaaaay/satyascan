from dataclasses import dataclass

from app.providers.base import FactCheckProvider, ImageSearchProvider, LLMProvider, TranslationProvider, WhatsAppClient
from app.vectorstore.base import VectorStore


@dataclass
class Providers:
    """Everything an agent node needs, threaded explicitly through the
    pipeline rather than resolved via per-node dependency injection - makes
    each node trivially testable by constructing a Providers of mocks."""

    llm: LLMProvider
    fact_check: FactCheckProvider
    image_search: ImageSearchProvider
    translation: TranslationProvider
    whatsapp: WhatsAppClient
    vectorstore: VectorStore


def build_providers() -> Providers:
    from app.config import get_settings
    from app.providers.factory import (
        get_fact_check_provider,
        get_image_search_provider,
        get_llm_provider,
        get_translation_provider,
        get_whatsapp_client,
    )
    from app.vectorstore.chroma_store import ChromaStore

    settings = get_settings()
    return Providers(
        llm=get_llm_provider(),
        fact_check=get_fact_check_provider(),
        image_search=get_image_search_provider(),
        translation=get_translation_provider(),
        whatsapp=get_whatsapp_client(),
        vectorstore=ChromaStore(persist_dir=settings.chroma_persist_dir),
    )


def build_mock_providers() -> Providers:
    """Convenience constructor for tests: every provider forced to its Mock
    implementation regardless of env vars."""
    from app.providers.fact_check.mock import MockFactCheckProvider
    from app.providers.image_search.mock import MockImageSearchProvider
    from app.providers.llm.mock import MockLLMProvider
    from app.providers.translation.mock import MockTranslationProvider
    from app.providers.whatsapp.mock import MockWhatsAppClient
    from app.vectorstore.chroma_store import ChromaStore
    import tempfile

    return Providers(
        llm=MockLLMProvider(),
        fact_check=MockFactCheckProvider(),
        image_search=MockImageSearchProvider(),
        translation=MockTranslationProvider(),
        whatsapp=MockWhatsAppClient(),
        vectorstore=ChromaStore(persist_dir=tempfile.mkdtemp()),
    )

import pytest

from app.agents import pipeline
from app.agents.state import IntentResult
from app.models.enums import IntentType, Language


@pytest.mark.asyncio
async def test_short_circuit_translates_for_every_non_english_language(base_state, providers):
    # Regression test: this used to only translate for Malayalam
    # (`if state.language_hint == Language.ml`), silently leaving Hindi/
    # Tamil users with an English chitchat reply.
    for language in (Language.ml, Language.hi, Language.ta):
        base_state.language_hint = language
        base_state.intent = IntentResult(intent_type=IntentType.chitchat, has_text_claim=False, has_image=False)

        result = await pipeline._short_circuit(base_state, providers)

        assert result.explanation.language == language
        # MockTranslationProvider.translate() returns a fixed, non-English
        # stand-in per target language rather than echoing the input text.
        assert result.explanation.text != pipeline._CHITCHAT_REPLY


@pytest.mark.asyncio
async def test_short_circuit_leaves_english_untranslated(base_state, providers):
    base_state.language_hint = Language.en
    base_state.intent = IntentResult(intent_type=IntentType.chitchat, has_text_claim=False, has_image=False)

    result = await pipeline._short_circuit(base_state, providers)

    assert result.explanation.text == pipeline._CHITCHAT_REPLY

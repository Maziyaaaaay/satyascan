import pytest

from app.agents import intent_analyzer


@pytest.mark.asyncio
async def test_text_only_sets_has_text_claim(base_state, providers):
    base_state.input_text = "Drinking hot water cures COVID"
    result = await intent_analyzer.run(base_state, providers)
    assert result.intent is not None
    assert result.intent.has_text_claim is True
    assert result.intent.has_image is False


@pytest.mark.asyncio
async def test_image_only_sets_has_image(base_state, providers):
    base_state.input_image_bytes = b"fake-image-bytes"
    result = await intent_analyzer.run(base_state, providers)
    assert result.intent.has_image is True
    assert result.intent.has_text_claim is False


@pytest.mark.asyncio
async def test_empty_message_sets_neither_flag(base_state, providers):
    result = await intent_analyzer.run(base_state, providers)
    assert result.intent.has_text_claim is False
    assert result.intent.has_image is False

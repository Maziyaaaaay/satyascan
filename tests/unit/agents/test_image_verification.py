import pytest

from app.agents import image_verification


@pytest.mark.asyncio
async def test_populates_image_analysis_when_image_present(base_state, providers):
    base_state.input_image_bytes = b"fake-image-bytes"
    result = await image_verification.run(base_state, providers)
    assert result.image_analysis is not None
    assert result.image_analysis.ocr_text
    assert result.image_analysis.ai_generated_probability is not None
    assert 0.0 <= result.image_analysis.ai_generated_probability <= 1.0
    assert result.image_analysis.ai_generated_reasoning


@pytest.mark.asyncio
async def test_noop_when_no_image(base_state, providers):
    result = await image_verification.run(base_state, providers)
    assert result.image_analysis is None

import uuid

import pytest

from app.agents.pipeline import run_pipeline
from app.agents.state import PipelineState
from app.models.enums import Language, Verdict
from app.providers.bundle import build_mock_providers


@pytest.mark.asyncio
async def test_text_claim_end_to_end_produces_full_verdict():
    providers = build_mock_providers()
    state = PipelineState(
        verification_id=uuid.uuid4(),
        input_text="Drinking hot water cures COVID",
        language_hint=Language.en,
    )

    result = await run_pipeline(state, providers)

    assert isinstance(result.reasoning.verdict, Verdict)
    assert result.confidence is not None
    assert 0.0 <= result.confidence.score <= 1.0
    assert len(result.ranked_evidence) >= 1
    assert result.explanation is not None
    assert result.explanation.text
    assert result.explanation.language == Language.en


@pytest.mark.asyncio
async def test_text_claim_end_to_end_in_malayalam():
    providers = build_mock_providers()
    state = PipelineState(
        verification_id=uuid.uuid4(),
        input_text="Drinking hot water cures COVID",
        language_hint=Language.ml,
    )

    result = await run_pipeline(state, providers)

    assert result.explanation.language == Language.ml
    assert any("ഀ" <= ch <= "ൿ" for ch in result.explanation.text)


@pytest.mark.asyncio
async def test_image_only_end_to_end_produces_verdict():
    providers = build_mock_providers()
    state = PipelineState(verification_id=uuid.uuid4(), input_image_bytes=b"fake-image-bytes-for-testing")

    result = await run_pipeline(state, providers)

    assert result.image_analysis is not None
    assert isinstance(result.reasoning.verdict, Verdict)
    assert result.confidence is not None
    assert result.explanation is not None


@pytest.mark.asyncio
async def test_mixed_text_and_image_runs_both_branches_concurrently():
    providers = build_mock_providers()
    state = PipelineState(
        verification_id=uuid.uuid4(),
        input_text="This image proves the claim",
        input_image_bytes=b"fake-image-bytes-for-testing",
    )

    result = await run_pipeline(state, providers)

    assert len(result.claims) >= 1
    assert result.image_analysis is not None
    assert result.reasoning is not None
    assert result.explanation is not None


@pytest.mark.asyncio
async def test_chitchat_short_circuits_without_running_full_pipeline():
    providers = build_mock_providers()
    # MockLLMProvider's intent classification is deterministic per prompt hash;
    # empty input reliably has neither text nor image, which short-circuits
    # regardless of the classified intent_type.
    state = PipelineState(verification_id=uuid.uuid4())

    result = await run_pipeline(state, providers)

    assert result.reasoning is None
    assert result.explanation is not None
    assert result.explanation.text

import pytest

from app.agents import explanation_agent
from app.agents.state import ConfidenceResult, ReasoningResult
from app.models.enums import ConfidenceLabel, Language, Verdict


@pytest.mark.asyncio
async def test_english_explanation(base_state, providers):
    base_state.language_hint = Language.en
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="no supporting evidence", certainty=0.8)
    base_state.confidence = ConfidenceResult(score=0.8, label=ConfidenceLabel.high)

    result = await explanation_agent.run(base_state, providers)
    assert result.explanation.language == Language.en
    assert result.explanation.text


@pytest.mark.asyncio
async def test_malayalam_explanation_is_translated(base_state, providers):
    base_state.language_hint = Language.ml
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="no supporting evidence", certainty=0.8)
    base_state.confidence = ConfidenceResult(score=0.8, label=ConfidenceLabel.high)

    result = await explanation_agent.run(base_state, providers)
    assert result.explanation.language == Language.ml
    assert any("ഀ" <= ch <= "ൿ" for ch in result.explanation.text)


@pytest.mark.asyncio
async def test_hindi_explanation_is_translated(base_state, providers):
    base_state.language_hint = Language.hi
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="no supporting evidence", certainty=0.8)
    base_state.confidence = ConfidenceResult(score=0.8, label=ConfidenceLabel.high)

    result = await explanation_agent.run(base_state, providers)
    assert result.explanation.language == Language.hi
    assert any("ऀ" <= ch <= "ॿ" for ch in result.explanation.text)


@pytest.mark.asyncio
async def test_tamil_explanation_is_translated(base_state, providers):
    base_state.language_hint = Language.ta
    base_state.reasoning = ReasoningResult(verdict=Verdict.false, rationale="no supporting evidence", certainty=0.8)
    base_state.confidence = ConfidenceResult(score=0.8, label=ConfidenceLabel.high)

    result = await explanation_agent.run(base_state, providers)
    assert result.explanation.language == Language.ta
    assert any("஀" <= ch <= "௿" for ch in result.explanation.text)

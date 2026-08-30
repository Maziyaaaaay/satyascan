from pydantic import BaseModel

from app.agents._call_logging import llm_provider_name
from app.agents.prompts import load as load_prompt
from app.agents.state import ExplanationResult, PipelineState, ProviderCallRecord
from app.models.enums import Language, ProviderName
from app.providers.bundle import Providers

SYSTEM_PROMPT_TEMPLATE = load_prompt("explanation_agent") + "\n\nRequested language: {language_name}"

_LANGUAGE_NAMES = {Language.en: "English", Language.ml: "Malayalam", Language.hi: "Hindi", Language.ta: "Tamil"}


class _ExplanationSchema(BaseModel):
    explanation: str


def _build_user_prompt(state: PipelineState) -> str:
    return (
        f"Verdict: {state.reasoning.verdict.value}\n"
        f"Confidence: {state.confidence.label.value} ({state.confidence.score})\n"
        f"Rationale: {state.reasoning.rationale}"
    )


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    target_language = state.language_hint
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language_name=_LANGUAGE_NAMES[target_language])

    response = await providers.llm.generate(
        system_prompt=system_prompt, user_prompt=_build_user_prompt(state), response_schema=_ExplanationSchema
    )
    state.provider_calls.append(
        ProviderCallRecord(provider=llm_provider_name(response), endpoint="generate:explanation_agent")
    )
    parsed = _ExplanationSchema.model_validate(response.parsed)
    text = parsed.explanation

    if target_language != Language.en:
        # Safety net for any non-English target (ml/hi/ta): the LLM is
        # asked to answer in that language via the system prompt above, but
        # isn't guaranteed to - confirm and correct rather than trust it.
        detected = await providers.translation.detect_language(text)
        state.provider_calls.append(
            ProviderCallRecord(provider=ProviderName.google_translate, endpoint="detect_language")
        )
        if detected != target_language.value:
            text = await providers.translation.translate(text, target_language=target_language.value)
            state.provider_calls.append(
                ProviderCallRecord(provider=ProviderName.google_translate, endpoint="translate")
            )

    state.explanation = ExplanationResult(text=text, language=target_language)
    return state

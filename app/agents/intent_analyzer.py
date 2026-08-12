from app.agents.prompts import load as load_prompt
from app.agents.state import IntentResult, PipelineState
from app.providers.bundle import Providers

SYSTEM_PROMPT = load_prompt("intent_analyzer")


def _build_user_prompt(state: PipelineState) -> str:
    parts = []
    if state.input_text:
        parts.append(f"Message text: {state.input_text}")
    if state.input_image_bytes is not None:
        parts.append("An image was attached to this message.")
    return "\n".join(parts) or "(empty message)"


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    response = await providers.llm.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(state),
        response_schema=IntentResult,
    )
    intent = IntentResult.model_validate(response.parsed)
    # Ground has_text_claim/has_image in what was actually received rather
    # than trusting the LLM to echo it back correctly.
    intent.has_text_claim = bool(state.input_text)
    intent.has_image = state.input_image_bytes is not None
    state.intent = intent
    return state

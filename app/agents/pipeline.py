import asyncio
from typing import List

from app.agents import (
    claim_extraction,
    confidence_scoring,
    evidence_ranking,
    explanation_agent,
    image_verification,
    intent_analyzer,
    reasoning_agent,
    search_agent,
)
from app.agents.state import ExplanationResult, PipelineState
from app.models.enums import IntentType, Language
from app.providers.bundle import Providers

_CHITCHAT_REPLY = "Hi! I'm SatyaScan. Forward me a message or image you'd like me to fact-check, and I'll look into it."
_UNCLEAR_REPLY = (
    "I couldn't find a specific claim to check in that message. "
    "Could you forward the exact text or image you'd like verified?"
)


async def run_pipeline(state: PipelineState, providers: Providers) -> PipelineState:
    """Intent Analyzer -> [Claim Extraction -> Search Agent] and/or
    [Image Verification] (concurrent, merged) -> Evidence Ranking ->
    Reasoning -> Confidence Scoring -> Explanation.

    Confidence Scoring is deliberately sequenced ahead of the Explanation
    Agent (unlike the PRD Part 5 catalog order) because the explanation text
    needs to state the confidence level.
    """
    state = await intent_analyzer.run(state, providers)

    if state.intent.intent_type in (IntentType.chitchat, IntentType.unclear) or not (
        state.intent.has_text_claim or state.intent.has_image
    ):
        return await _short_circuit(state, providers)

    branches = []
    if state.intent.has_text_claim:
        branches.append(_run_text_path(state, providers))
    if state.intent.has_image:
        branches.append(_run_image_path(state, providers))

    partial_states = await asyncio.gather(*branches)
    _merge_partial_states(state, partial_states)

    state = await evidence_ranking.run(state, providers)
    state = await reasoning_agent.run(state, providers)
    state = await confidence_scoring.run(state, providers)
    state = await explanation_agent.run(state, providers)
    return state


async def _run_text_path(state: PipelineState, providers: Providers) -> PipelineState:
    branch_state = state.model_copy()
    branch_state = await claim_extraction.run(branch_state, providers)
    branch_state = await search_agent.run(branch_state, providers)
    return branch_state


async def _run_image_path(state: PipelineState, providers: Providers) -> PipelineState:
    branch_state = state.model_copy()
    branch_state = await image_verification.run(branch_state, providers)
    return branch_state


def _merge_partial_states(state: PipelineState, partials: List[PipelineState]) -> None:
    for partial in partials:
        if partial.claims:
            state.claims = partial.claims
        if partial.search is not None:
            state.search = partial.search
        if partial.image_analysis is not None:
            state.image_analysis = partial.image_analysis


async def _short_circuit(state: PipelineState, providers: Providers) -> PipelineState:
    text = _CHITCHAT_REPLY if state.intent.intent_type == IntentType.chitchat else _UNCLEAR_REPLY
    if state.language_hint == Language.ml:
        text = await providers.translation.translate(text, target_language="ml")
    state.explanation = ExplanationResult(text=text, language=state.language_hint)
    return state

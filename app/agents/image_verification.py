from app.agents.state import ImageAnalysisResult, PipelineState, ProviderCallRecord
from app.models.enums import ProviderName
from app.providers.bundle import Providers


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    if state.input_image_bytes is None:
        return state

    ocr_result = await providers.image_search.extract_text(state.input_image_bytes)
    state.provider_calls.append(ProviderCallRecord(provider=ProviderName.google_vision, endpoint="extract_text"))

    matches = await providers.image_search.reverse_image_search(state.input_image_bytes)
    state.provider_calls.append(
        ProviderCallRecord(provider=ProviderName.google_vision, endpoint="reverse_image_search")
    )

    ai_detection = await providers.ai_detection.detect(state.input_image_bytes)
    state.provider_calls.append(ProviderCallRecord(provider=ProviderName.sightengine, endpoint="detect"))

    state.image_analysis = ImageAnalysisResult(
        ocr_text=ocr_result.text,
        reverse_matches=matches,
        ai_generated_probability=ai_detection.ai_generated_probability,
        ai_generated_reasoning=ai_detection.reasoning,
    )
    return state

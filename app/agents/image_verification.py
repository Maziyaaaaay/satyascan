from app.agents.state import ImageAnalysisResult, PipelineState, ProviderCallRecord
from app.models.enums import ProviderName
from app.providers.bundle import Providers
from app.services import c2pa_service


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

    # C2PA is a local metadata read, not an external provider call (no
    # network/API key involved) - not recorded as a ProviderCallRecord.
    c2pa_result = c2pa_service.check_manifest(state.input_image_bytes)

    state.image_analysis = ImageAnalysisResult(
        ocr_text=ocr_result.text,
        reverse_matches=matches,
        ai_generated_probability=ai_detection.ai_generated_probability,
        ai_generated_reasoning=ai_detection.reasoning,
        c2pa_has_manifest=c2pa_result.has_manifest,
        c2pa_generator=c2pa_result.generator,
        c2pa_digital_source_type=c2pa_result.digital_source_type,
        c2pa_is_ai_indicated=c2pa_result.is_ai_indicated,
        c2pa_summary=c2pa_result.summary,
    )
    return state

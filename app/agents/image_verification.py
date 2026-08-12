from app.agents.state import ImageAnalysisResult, PipelineState
from app.providers.bundle import Providers


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    if state.input_image_bytes is None:
        return state

    ocr_result = await providers.image_search.extract_text(state.input_image_bytes)
    matches = await providers.image_search.reverse_image_search(state.input_image_bytes)
    state.image_analysis = ImageAnalysisResult(ocr_text=ocr_result.text, reverse_matches=matches)
    return state

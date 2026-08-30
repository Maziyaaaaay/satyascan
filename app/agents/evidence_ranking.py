from typing import Optional
from urllib.parse import urlparse

from app.agents.state import PipelineState, ProviderCallRecord, RankedEvidence
from app.models.enums import ProviderName, Stance
from app.providers.bundle import Providers
from app.vectorstore.base import VectorStoreItem

_RATING_STANCE_MAP = {
    "false": Stance.contradicts,
    "misleading": Stance.contradicts,
    "partly false": Stance.contradicts,
    "true": Stance.supports,
    "unproven": Stance.neutral,
}


def _stance_from_rating(rating: Optional[str]) -> Stance:
    if not rating:
        return Stance.neutral
    return _RATING_STANCE_MAP.get(rating.strip().lower(), Stance.neutral)


def _domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return urlparse(url).netloc or None


async def run(state: PipelineState, providers: Providers) -> PipelineState:
    # An image sent with no caption and nothing extracted via OCR leaves
    # both input_text and every claim empty - falling back to "" here used
    # to reach providers.llm.embed() with an empty string, which Gemini's
    # embed_content rejects outright ("'content' argument must not be
    # empty"), crashing the whole verification. OCR text is a reasonable
    # stand-in query when there's no caption; "image content" is the last
    # resort so embed() is never called with nothing at all.
    if state.claims:
        query_text = state.claims[0].normalized_text
    else:
        ocr_text = state.image_analysis.ocr_text if state.image_analysis else None
        query_text = state.input_text or ocr_text or "image content"
    fact_checks = state.search.fact_checks if state.search else []
    image_matches = state.image_analysis.reverse_matches if state.image_analysis else []

    if not fact_checks and not image_matches:
        state.ranked_evidence = []
        return state

    evidence_texts = []
    evidence_meta = []
    for fc in fact_checks:
        evidence_texts.append(f"{fc.rating or 'unknown'}: {fc.claim_text}")
        evidence_meta.append(
            {
                "type": "fact_check",
                "url": fc.url or "",
                "domain": _domain(fc.url) or "",
                "stance": _stance_from_rating(fc.rating).value,
                "is_live_search": fc.publisher == "Live web search",
            }
        )
    for match in image_matches:
        evidence_texts.append(f"image match: {match.page_title or match.url}")
        evidence_meta.append(
            {
                "type": "image_match",
                "url": match.url,
                "domain": _domain(match.url) or "",
                "stance": Stance.neutral.value,
            }
        )

    embeddings = await providers.llm.embed([query_text] + evidence_texts)
    state.provider_calls.append(ProviderCallRecord(provider=ProviderName.gemini, endpoint="embed"))
    query_embedding, evidence_embeddings = embeddings[0], embeddings[1:]

    # Chroma collection names must be alphanumeric/underscore/hyphen only.
    collection = f"verification-{state.verification_id.hex}"
    items = [
        VectorStoreItem(
            id=str(i), text=evidence_texts[i], embedding=evidence_embeddings[i], metadata=evidence_meta[i]
        )
        for i in range(len(evidence_texts))
    ]
    await providers.vectorstore.upsert(collection, items)
    matches = await providers.vectorstore.query(collection, query_embedding, top_k=len(evidence_texts))

    ranked = []
    for rank, match in enumerate(matches, start=1):
        relevance = min(1.0, max(0.0, 1.0 - match.distance))
        ranked.append(
            RankedEvidence(
                claim_snippet=match.text,
                source_url=match.metadata.get("url") or None,
                source_domain=match.metadata.get("domain") or None,
                stance=Stance(match.metadata.get("stance", Stance.neutral.value)),
                relevance_score=round(relevance, 4),
                rank=rank,
                is_live_search=bool(match.metadata.get("is_live_search", False)),
            )
        )
    state.ranked_evidence = ranked
    return state

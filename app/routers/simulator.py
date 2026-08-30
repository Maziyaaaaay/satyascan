import base64
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.logging_conf import get_logger
from app.models.enums import Channel, Language
from app.models.evidence import Evidence
from app.models.image import Image
from app.providers.bundle import Providers, build_providers
from app.services import verification_service
from app.services.rate_limit_service import RateLimitExceeded

router = APIRouter()
logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).parent.parent / "static" / "simulator"


def get_providers() -> Providers:
    return build_providers()


class SimulatorMessageRequest(BaseModel):
    session_id: str
    text: Optional[str] = None
    image_base64: Optional[str] = None
    language: Language = Language.en


class SourceInfo(BaseModel):
    url: str
    domain: str


class SimulatorMessageResponse(BaseModel):
    verdict: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_label: Optional[str] = None
    explanation: Optional[str] = None
    rationale: Optional[str] = None
    sources: List[SourceInfo] = []
    image_match_count: Optional[int] = None
    image_ocr_text: Optional[str] = None
    ai_generated_probability: Optional[float] = None
    ai_generated_reasoning: Optional[str] = None
    c2pa_has_manifest: Optional[bool] = None
    c2pa_generator: Optional[str] = None
    c2pa_is_ai_indicated: Optional[bool] = None
    c2pa_summary: Optional[str] = None


@router.get("/simulator")
async def simulator_page():
    return FileResponse(_STATIC_DIR / "index.html")


@router.post("/simulator/message", response_model=SimulatorMessageResponse)
async def simulator_message(
    body: SimulatorMessageRequest,
    db: AsyncSession = Depends(get_db),
    providers: Providers = Depends(get_providers),
):
    image_bytes = base64.b64decode(body.image_base64) if body.image_base64 else None

    try:
        verification = await verification_service.process_incoming(
            db,
            providers,
            channel=Channel.simulator,
            external_user_id=f"sim:{body.session_id}",
            text=body.text,
            image_bytes=image_bytes,
            preferred_language=body.language,
        )
    except RateLimitExceeded:
        return SimulatorMessageResponse(
            explanation="You're sending messages too quickly - please wait a moment and try again."
        )
    except Exception:
        logger.exception("verification_pipeline_failed", channel=Channel.simulator.value)
        return SimulatorMessageResponse(
            explanation="Sorry, I ran into a problem checking that. Please try again in a moment."
        )

    evidence_result = await db.execute(
        select(Evidence)
        .options(selectinload(Evidence.source))
        .where(Evidence.verification_id == verification.id)
        .order_by(Evidence.rank)
    )
    sources = [
        SourceInfo(url=e.source.url, domain=e.source.domain)
        for e in evidence_result.scalars().all()
        if e.source is not None
    ]

    image_match_count: Optional[int] = None
    image_ocr_text: Optional[str] = None
    ai_generated_probability: Optional[float] = None
    ai_generated_reasoning: Optional[str] = None
    c2pa_has_manifest: Optional[bool] = None
    c2pa_generator: Optional[str] = None
    c2pa_is_ai_indicated: Optional[bool] = None
    c2pa_summary: Optional[str] = None
    if verification.has_image:
        image_result = await db.execute(select(Image).where(Image.verification_id == verification.id))
        image = image_result.scalar_one_or_none()
        if image is not None:
            image_match_count = image.reverse_search_match_count
            image_ocr_text = image.ocr_text_excerpt
            ai_generated_probability = image.ai_generated_probability
            ai_generated_reasoning = image.ai_generated_reasoning
            c2pa_has_manifest = image.c2pa_has_manifest
            c2pa_generator = image.c2pa_generator
            c2pa_is_ai_indicated = image.c2pa_is_ai_indicated
            c2pa_summary = image.c2pa_summary

    return SimulatorMessageResponse(
        verdict=verification.verdict.value if verification.verdict else None,
        confidence_score=verification.confidence_score,
        confidence_label=verification.confidence_label.value if verification.confidence_label else None,
        explanation=verification.explanation_text,
        rationale=verification.rationale,
        sources=sources,
        image_match_count=image_match_count,
        image_ocr_text=image_ocr_text,
        ai_generated_probability=ai_generated_probability,
        ai_generated_reasoning=ai_generated_reasoning,
        c2pa_has_manifest=c2pa_has_manifest,
        c2pa_generator=c2pa_generator,
        c2pa_is_ai_indicated=c2pa_is_ai_indicated,
        c2pa_summary=c2pa_summary,
    )

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
from app.models.enums import Channel, Language
from app.models.evidence import Evidence
from app.providers.bundle import Providers, build_providers
from app.services import verification_service
from app.services.rate_limit_service import RateLimitExceeded

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static" / "simulator"


def get_providers() -> Providers:
    return build_providers()


class SimulatorMessageRequest(BaseModel):
    session_id: str
    text: Optional[str] = None
    image_base64: Optional[str] = None
    language: Language = Language.en


class SimulatorMessageResponse(BaseModel):
    verdict: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_label: Optional[str] = None
    explanation: Optional[str] = None
    sources: List[str] = []


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

    result = await db.execute(
        select(Evidence)
        .options(selectinload(Evidence.source))
        .where(Evidence.verification_id == verification.id)
        .order_by(Evidence.rank)
    )
    sources = [e.source.url for e in result.scalars().all() if e.source is not None]

    return SimulatorMessageResponse(
        verdict=verification.verdict.value if verification.verdict else None,
        confidence_score=verification.confidence_score,
        confidence_label=verification.confidence_label.value if verification.confidence_label else None,
        explanation=verification.explanation_text,
        sources=sources,
    )

import hashlib
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import run_pipeline
from app.agents.state import PipelineState
from app.logging_conf import get_logger
from app.models.api_log import APILog
from app.models.enums import (
    Channel,
    EvidenceType,
    Language,
    MessageDirection,
    ProviderName,
    SourceMediaType,
    VerificationStatus,
)
from app.models.evidence import Evidence
from app.models.message import EXCERPT_MAX_LEN, Message
from app.models.mixins import utcnow
from app.models.source import Source
from app.models.user import User
from app.models.verification import Verification
from app.providers.bundle import Providers
from app.security.encryption import encrypt, hash_for_lookup
from app.services import consent_service, media_service, rate_limit_service
from app.services.rate_limit_service import RateLimitExceeded

logger = get_logger(__name__)


async def process_incoming(
    db: AsyncSession,
    providers: Providers,
    *,
    channel: Channel,
    external_user_id: str,
    text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    external_message_id: Optional[str] = None,
    preferred_language: Optional[Language] = None,
    source_media_type: SourceMediaType = SourceMediaType.text,
) -> Verification:
    """Single entrypoint for turning an inbound message (from any client)
    into a completed Verification. The WhatsApp webhook and the local
    simulator both call this identically, proving both client paths exercise
    the same internal logic."""
    try:
        rate_limit_service.get_rate_limiter().check(external_user_id)
    except RateLimitExceeded:
        logger.warning("rate_limit_exceeded", channel=channel.value)
        raise

    user, _ = await get_or_create_user(db, channel, external_user_id, preferred_language)

    verification = Verification(
        user_id=user.id,
        has_image=image_bytes is not None,
        status=VerificationStatus.processing,
        source_media_type=source_media_type,
    )
    db.add(verification)
    await db.flush()
    logger.info(
        "verification_started",
        verification_id=str(verification.id),
        channel=channel.value,
        has_text=text is not None,
        has_image=image_bytes is not None,
    )

    await _record_message(db, verification, channel, text, external_message_id, user)

    image_record = None
    if image_bytes is not None:
        image_record = await media_service.record_image_metadata(db, verification, image_bytes)

    start = time.monotonic()
    state = PipelineState(
        verification_id=verification.id,
        input_text=text,
        input_image_bytes=image_bytes,
        language_hint=user.preferred_language,
    )
    state = await run_pipeline(state, providers)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    if image_record is not None and state.image_analysis is not None:
        await media_service.finalize_image_summary(
            db,
            image_record,
            state.image_analysis.ocr_text,
            len(state.image_analysis.reverse_matches),
            ai_generated_probability=state.image_analysis.ai_generated_probability,
            ai_generated_reasoning=state.image_analysis.ai_generated_reasoning,
            c2pa_has_manifest=state.image_analysis.c2pa_has_manifest,
            c2pa_generator=state.image_analysis.c2pa_generator,
            c2pa_digital_source_type=state.image_analysis.c2pa_digital_source_type,
            c2pa_is_ai_indicated=state.image_analysis.c2pa_is_ai_indicated,
            c2pa_summary=state.image_analysis.c2pa_summary,
        )

    await _persist_pipeline_result(db, verification, state, elapsed_ms, providers)
    logger.info(
        "verification_completed",
        verification_id=str(verification.id),
        verdict=verification.verdict.value if verification.verdict else None,
        confidence_score=verification.confidence_score,
        processing_time_ms=elapsed_ms,
    )
    return verification


def _is_mock_provider(instance: object) -> bool:
    return type(instance).__name__.startswith("Mock")


async def get_or_create_user(
    db: AsyncSession, channel: Channel, external_user_id: str, preferred_language: Optional[Language]
) -> tuple[User, bool]:
    """Returns (user, is_new) - is_new lets callers (e.g. the WhatsApp
    webhook) special-case a caller's very first-ever message."""
    lookup_hash = hash_for_lookup(external_user_id)
    result = await db.execute(select(User).where(User.phone_number_hash == lookup_hash))
    user = result.scalar_one_or_none()

    if user is not None:
        user.last_active_at = utcnow()
        if preferred_language is not None:
            user.preferred_language = preferred_language
        await db.flush()
        return user, False

    user = User(
        phone_number_encrypted=encrypt(external_user_id),
        phone_number_hash=lookup_hash,
        channel=channel,
        preferred_language=preferred_language or Language.en,
    )
    db.add(user)
    await db.flush()
    return user, True


async def _record_message(
    db: AsyncSession,
    verification: Verification,
    channel: Channel,
    text: Optional[str],
    external_message_id: Optional[str],
    user: User,
) -> None:
    if text is None:
        return
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    excerpt = text[:EXCERPT_MAX_LEN] if consent_service.should_store_excerpt(user) else None
    db.add(
        Message(
            verification_id=verification.id,
            direction=MessageDirection.inbound,
            channel=channel,
            external_message_id=external_message_id,
            content_hash=content_hash,
            content_excerpt=excerpt,
        )
    )
    await db.flush()


async def _get_or_create_source(db: AsyncSession, url: str, domain: Optional[str]) -> Source:
    result = await db.execute(select(Source).where(Source.url == url))
    source = result.scalar_one_or_none()
    if source is not None:
        source.last_used_at = utcnow()
        return source

    source = Source(url=url, domain=domain or "")
    db.add(source)
    await db.flush()
    return source


_PROVIDER_TO_BUNDLE_ATTR = {
    ProviderName.gemini: "llm",
    ProviderName.openai: "llm",
    ProviderName.google_fact_check: "fact_check",
    ProviderName.google_vision: "image_search",
    ProviderName.sightengine: "ai_detection",
    ProviderName.google_translate: "translation",
    ProviderName.whatsapp: "whatsapp",
    ProviderName.openai_whisper: "speech_to_text",
    ProviderName.serper: "web_search",
}


async def _persist_pipeline_result(
    db: AsyncSession, verification: Verification, state: PipelineState, elapsed_ms: int, providers: Providers
) -> None:
    claim_text = state.claims[0].normalized_text if state.claims else state.input_text
    verification.claim_text = claim_text
    verification.claim_text_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest() if claim_text else None
    verification.intent_type = state.intent.intent_type if state.intent else None
    verification.processing_time_ms = elapsed_ms
    verification.completed_at = utcnow()
    verification.status = VerificationStatus.completed

    if state.reasoning is not None:
        verification.verdict = state.reasoning.verdict
        verification.rationale = state.reasoning.rationale
    if state.confidence is not None:
        verification.confidence_score = state.confidence.score
        verification.confidence_label = state.confidence.label
    if state.explanation is not None:
        verification.explanation_text = state.explanation.text
        verification.explanation_language = state.explanation.language
    verification.is_live_search_confirmed = any(e.is_live_search for e in state.ranked_evidence)

    for evidence in state.ranked_evidence:
        source = None
        if evidence.source_url:
            source = await _get_or_create_source(db, evidence.source_url, evidence.source_domain)
        db.add(
            Evidence(
                verification_id=verification.id,
                source_id=source.id if source else None,
                evidence_type=EvidenceType.fact_check,
                claim_snippet=evidence.claim_snippet,
                relevance_score=evidence.relevance_score,
                stance=evidence.stance,
                rank=evidence.rank,
            )
        )

    for call in state.provider_calls:
        bundle_attr = _PROVIDER_TO_BUNDLE_ATTR[call.provider]
        db.add(
            APILog(
                verification_id=verification.id,
                provider=call.provider,
                endpoint=call.endpoint,
                is_mock=_is_mock_provider(getattr(providers, bundle_attr)),
            )
        )

    await db.flush()

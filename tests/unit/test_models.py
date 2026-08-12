import hashlib

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import (
    Channel,
    ConfidenceLabel,
    EvidenceType,
    FeedbackRating,
    IntentType,
    Language,
    MessageDirection,
    ProviderName,
    Stance,
    Verdict,
    VerificationStatus,
)
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.source import Source
from app.models.user import User
from app.models.verification import Verification


@pytest.mark.asyncio
async def test_full_verification_graph_persists_and_loads(db_session):
    user = User(
        phone_number_encrypted="encrypted-blob",
        phone_number_hash=hashlib.sha256(b"+911234567890").hexdigest(),
        channel=Channel.whatsapp,
        preferred_language=Language.ml,
        consent_given=True,
    )
    db_session.add(user)
    await db_session.flush()

    verification = Verification(
        user_id=user.id,
        claim_text="Drinking hot water cures COVID",
        claim_text_hash=hashlib.sha256(b"drinking hot water cures covid").hexdigest(),
        intent_type=IntentType.factual_claim,
        verdict=Verdict.false,
        confidence_score=0.92,
        confidence_label=ConfidenceLabel.high,
        explanation_text="No credible evidence supports this claim.",
        explanation_language=Language.en,
        status=VerificationStatus.completed,
    )
    db_session.add(verification)
    await db_session.flush()

    source = Source(url="https://example.org/fact-check-1", domain="example.org")
    db_session.add(source)
    await db_session.flush()

    db_session.add(
        Evidence(
            verification_id=verification.id,
            source_id=source.id,
            evidence_type=EvidenceType.fact_check,
            claim_snippet="No scientific evidence hot water cures viral infections.",
            relevance_score=0.95,
            stance=Stance.contradicts,
            rank=1,
        )
    )
    db_session.add(
        Message(
            verification_id=verification.id,
            direction=MessageDirection.inbound,
            channel=Channel.whatsapp,
            content_hash=hashlib.sha256(b"forwarded message").hexdigest(),
        )
    )
    db_session.add(
        Feedback(verification_id=verification.id, user_id=user.id, rating=FeedbackRating.helpful)
    )
    await db_session.commit()

    loaded = (
        await db_session.execute(
            select(Verification)
            .options(
                selectinload(Verification.user),
                selectinload(Verification.evidence_items).selectinload(Evidence.source),
                selectinload(Verification.messages),
                selectinload(Verification.feedback_items),
            )
            .where(Verification.id == verification.id)
        )
    ).scalar_one()

    assert loaded.verdict == Verdict.false
    assert loaded.user.phone_number_hash == user.phone_number_hash
    assert len(loaded.evidence_items) == 1
    assert loaded.evidence_items[0].source.domain == "example.org"
    assert len(loaded.messages) == 1
    assert len(loaded.feedback_items) == 1


@pytest.mark.asyncio
async def test_message_defaults_to_no_stored_excerpt(db_session):
    verification = Verification()
    db_session.add(verification)
    await db_session.flush()

    message = Message(
        verification_id=verification.id,
        direction=MessageDirection.inbound,
        channel=Channel.simulator,
        content_hash="deadbeef",
    )
    db_session.add(message)
    await db_session.commit()

    assert message.content_excerpt is None


@pytest.mark.asyncio
async def test_api_log_defaults_is_mock_true(db_session):
    from app.models.api_log import APILog

    log = APILog(provider=ProviderName.gemini, endpoint="generate")
    db_session.add(log)
    await db_session.commit()

    assert log.is_mock is True

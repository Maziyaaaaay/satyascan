from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import get_session_factory
from app.db.session import get_db
from app.logging_conf import get_logger
from app.models.enums import Channel, ConfidenceLabel, Language, Verdict
from app.models.image import Image
from app.models.verification import Verification
from app.models.webhook_event import WebhookEvent
from app.providers.bundle import Providers, build_providers
from app.security.signature import verify_signature
from app.services import verification_service
from app.services.rate_limit_service import RateLimitExceeded

router = APIRouter()
logger = get_logger(__name__)

# Only en/ml are supported end-to-end (see app/models/enums.py Language) -
# any other detected language falls back to English rather than erroring.
_DETECTED_LANGUAGE_MAP = {"ml": Language.ml, "en": Language.en}

_WELCOME_TEXT = {
    Language.en: (
        "Hi! I'm SatyaScan. Forward me a message, image, or video you'd like "
        "me to fact-check, and I'll look into it."
    ),
    Language.ml: (
        "ഹായ്! ഞാൻ സത്യസ്‌കാൻ ആണ്. നിങ്ങൾക്ക് പരിശോധിക്കേണ്ട സന്ദേശം, ചിത്രം, "
        "അല്ലെങ്കിൽ വീഡിയോ എനിക്ക് ഫോർവേഡ് ചെയ്യൂ, ഞാൻ അത് പരിശോധിക്കാം."
    ),
}

_VERDICT_LABELS = {
    Language.en: {
        (Verdict.true, True): "TRUE",
        (Verdict.true, False): "LIKELY TRUE",
        (Verdict.false, True): "FALSE",
        (Verdict.false, False): "LIKELY FALSE",
        (Verdict.misleading, True): "MISLEADING",
        (Verdict.misleading, False): "MISLEADING",
        (Verdict.unverifiable, True): "UNVERIFIABLE",
        (Verdict.unverifiable, False): "UNVERIFIABLE",
        (Verdict.satire, True): "SATIRE",
        (Verdict.satire, False): "SATIRE",
    },
    Language.ml: {
        (Verdict.true, True): "ശരി",
        (Verdict.true, False): "മിക്കവാറും ശരി",
        (Verdict.false, True): "തെറ്റ്",
        (Verdict.false, False): "മിക്കവാറും തെറ്റ്",
        (Verdict.misleading, True): "തെറ്റിദ്ധരിപ്പിക്കുന്നത്",
        (Verdict.misleading, False): "തെറ്റിദ്ധരിപ്പിക്കുന്നത്",
        (Verdict.unverifiable, True): "സ്ഥിരീകരിക്കാൻ കഴിയില്ല",
        (Verdict.unverifiable, False): "സ്ഥിരീകരിക്കാൻ കഴിയില്ല",
        (Verdict.satire, True): "ആക്ഷേപഹാസ്യം",
        (Verdict.satire, False): "ആക്ഷേപഹാസ്യം",
    },
}

_LABELS = {
    Language.en: {"verdict": "Verdict", "confidence": "Confidence", "summary": "Summary", "image": "Image check"},
    Language.ml: {
        "verdict": "വിധി",
        "confidence": "വിശ്വാസ്യത",
        "summary": "ചുരുക്കം",
        "image": "ചിത്ര പരിശോധന",
    },
}

_IMAGE_VERDICT_TEXT = {
    Language.en: {
        "ai": "This image appears to be AI-generated or fabricated.",
        "real": "This image appears to be a real, unedited photo.",
        "unsure": "Could not confidently determine if this image is AI-generated.",
    },
    Language.ml: {
        "ai": "ഈ ചിത്രം AI ഉപയോഗിച്ച് നിർമ്മിച്ചതോ കൃത്രിമമായി ഉണ്ടാക്കിയതോ ആകാം.",
        "real": "ഈ ചിത്രം യഥാർത്ഥവും തിരുത്തപ്പെടാത്തതുമായ ഫോട്ടോ ആണെന്ന് തോന്നുന്നു.",
        "unsure": "ഈ ചിത്രം AI നിർമ്മിതമാണോ എന്ന് ഉറപ്പിച്ച് പറയാൻ കഴിയില്ല.",
    },
}


def _verdict_label(verdict: Optional[Verdict], confidence_label: Optional[ConfidenceLabel], language: Language) -> str:
    if verdict is None:
        return _VERDICT_LABELS[language][(Verdict.unverifiable, True)]
    is_high_confidence = confidence_label == ConfidenceLabel.high
    return _VERDICT_LABELS[language][(verdict, is_high_confidence)]


def _image_verdict_text(ai_generated_probability: Optional[float], language: Language) -> str:
    texts = _IMAGE_VERDICT_TEXT[language]
    if ai_generated_probability is None:
        return texts["unsure"]
    if ai_generated_probability >= 0.6:
        return texts["ai"]
    if ai_generated_probability <= 0.3:
        return texts["real"]
    return texts["unsure"]


async def _build_reply_text(db: AsyncSession, verification: Verification, language: Language) -> str:
    if verification.verdict is None:
        # No verdict means the pipeline took its chitchat/unclear
        # short-circuit (see _short_circuit in app/agents/pipeline.py) - that
        # path already produces a plain, ready-to-send reply, so wrapping it
        # in the Verdict/Confidence template would show a nonsensical
        # "Verdict: UNVERIFIABLE, Confidence: 0/100" for a greeting.
        return verification.explanation_text or ""

    labels = _LABELS[language]
    confidence_pct = round((verification.confidence_score or 0.0) * 100)
    lines = [
        f"{labels['verdict']}: {_verdict_label(verification.verdict, verification.confidence_label, language)}",
        f"{labels['confidence']}: {confidence_pct}/100",
        "",
        f"{labels['summary']}: {verification.explanation_text or ''}".strip(),
    ]

    if verification.has_image:
        image_result = await db.execute(select(Image).where(Image.verification_id == verification.id))
        image = image_result.scalar_one_or_none()
        if image is not None:
            image_line = _image_verdict_text(image.ai_generated_probability, language)
            if image.ai_generated_reasoning:
                image_line = f"{image_line} {image.ai_generated_reasoning}"
            lines.append("")
            lines.append(f"{labels['image']}: {image_line}")

    return "\n".join(lines).strip()


def get_providers() -> Providers:
    return build_providers()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == (settings.whatsapp_verify_token or ""):
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook/whatsapp")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    providers: Providers = Depends(get_providers),
):
    # Signature verification needs the exact raw bytes Meta signed, so this
    # reads the body directly rather than declaring a Pydantic body param
    # (which would consume/parse the stream first).
    raw_body = await request.body()
    settings = get_settings()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(raw_body, signature, settings.whatsapp_app_secret):
        return Response(status_code=403)
    if not settings.whatsapp_app_secret:
        logger.warning("whatsapp_webhook_signature_check_skipped", reason="WHATSAPP_APP_SECRET not set")

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                await _handle_message(message, db, providers)

    return {"status": "received"}


async def _claim_message(message_id: Optional[str]) -> bool:
    """Atomically claims message_id in its own immediately-committed
    transaction, before the (potentially slow) verification pipeline runs.
    Returns False if it was already claimed - WhatsApp delivers webhooks
    at-least-once and retries on a slow response, which without this produced
    duplicate replies to a single inbound message."""
    if not message_id:
        return True
    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(WebhookEvent(external_message_id=message_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False
    return True


async def _handle_message(message: dict, db: AsyncSession, providers: Providers) -> None:
    from_number = message.get("from")
    message_id = message.get("id")
    if from_number is None:
        return

    if not await _claim_message(message_id):
        logger.info("webhook_duplicate_message_ignored", message_id=message_id)
        return

    _, is_new_user = await verification_service.get_or_create_user(db, Channel.whatsapp, from_number, None)
    if is_new_user:
        # Committed immediately (rather than waiting for get_db()'s
        # end-of-request commit) so this user is durably on record even if a
        # later message in the same webhook payload raises and rolls back the
        # shared session - mirrors the reasoning behind _claim_message above.
        await db.commit()
        if message_id:
            await providers.whatsapp.mark_as_read(message_id)
        peek_text = (message.get("text") or {}).get("body") if message.get("type") == "text" else None
        welcome_language = await _detect_language(providers, peek_text) or Language.en
        await providers.whatsapp.send_text_message(from_number, _WELCOME_TEXT[welcome_language])
        return

    text: Optional[str] = None
    image_bytes: Optional[bytes] = None

    message_type = message.get("type")
    if message_type == "text":
        text = (message.get("text") or {}).get("body")
    elif message_type == "image":
        image_field = message.get("image") or {}
        media_id = image_field.get("id")
        if media_id:
            image_bytes = await providers.whatsapp.download_media(media_id)
        text = image_field.get("caption")
    elif message_type in ("audio", "voice"):
        # WhatsApp voice notes and forwarded audio files both arrive as
        # type "audio" (Cloud API has no separate "voice" type - "voice" is
        # kept here only in case that ever changes upstream).
        audio_field = message.get("audio") or message.get("voice") or {}
        media_id = audio_field.get("id")
        if media_id:
            audio_bytes = await providers.whatsapp.download_media(media_id)
            text = await providers.speech_to_text.transcribe(audio_bytes, mime_type=audio_field.get("mime_type"))

    preferred_language = await _detect_language(providers, text)

    try:
        verification = await verification_service.process_incoming(
            db,
            providers,
            channel=Channel.whatsapp,
            external_user_id=from_number,
            text=text,
            image_bytes=image_bytes,
            external_message_id=message_id,
            preferred_language=preferred_language,
        )
    except RateLimitExceeded:
        await providers.whatsapp.send_text_message(
            from_number, "You're sending messages too quickly - please wait a moment and try again."
        )
        return

    if message_id:
        await providers.whatsapp.mark_as_read(message_id)

    reply_language = verification.explanation_language or preferred_language or Language.en
    reply_text = await _build_reply_text(db, verification, reply_language)
    await providers.whatsapp.send_text_message(from_number, reply_text or "Sorry, I couldn't process that message.")


async def _detect_language(providers: Providers, text: Optional[str]) -> Optional[Language]:
    if not text or not text.strip():
        return None
    try:
        detected = await providers.translation.detect_language(text)
    except Exception:
        return None
    return _DETECTED_LANGUAGE_MAP.get(detected)

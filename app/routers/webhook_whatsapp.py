from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import get_session_factory
from app.db.session import get_db
from app.logging_conf import get_logger
from app.models.enums import Channel, Language
from app.models.image import Image
from app.models.verification import Verification
from app.models.webhook_event import WebhookEvent
from app.providers.base import InteractiveButton
from app.providers.bundle import Providers, build_providers
from app.security.signature import verify_signature
from app.services import report_formatting, verification_service, video_processing
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

_HOW_IT_WORKS_TEXT = {
    Language.en: (
        "*How SatyaScan works:*\n"
        "1. Forward a suspicious message, image, or video here.\n"
        "2. I check it against live web search, published fact-checks, and "
        "(for images/video) AI-generation and content-provenance signals.\n"
        "3. You get a verdict, a confidence score, and a plain-language "
        "explanation - in English or Malayalam."
    ),
    Language.ml: (
        "*സത്യസ്‌കാൻ എങ്ങനെ പ്രവർത്തിക്കുന്നു:*\n"
        "1. സംശയാസ്‌പദമായ സന്ദേശം, ചിത്രം, അല്ലെങ്കിൽ വീഡിയോ ഇവിടെ ഫോർവേഡ് ചെയ്യുക.\n"
        "2. ലൈവ് വെബ് സെർച്ച്, പ്രസിദ്ധീകരിച്ച ഫാക്ട്-ചെക്കുകൾ, കൂടാതെ "
        "(ചിത്രം/വീഡിയോയ്ക്ക്) AI-നിർമ്മാണ, ഉറവിട സൂചനകൾ എന്നിവ ഉപയോഗിച്ച് ഞാൻ ഇത് പരിശോധിക്കും.\n"
        "3. നിങ്ങൾക്ക് ഒരു വിധി, ഒരു വിശ്വാസ്യതാ സ്‌കോർ, ലളിതമായ ഒരു വിശദീകരണം എന്നിവ ലഭിക്കും - "
        "ഇംഗ്ലീഷിലോ മലയാളത്തിലോ."
    ),
}

_BUTTON_LABELS = {
    Language.en: {"check_another": "🔁 Check another", "how_it_works": "❔ How it works"},
    Language.ml: {"check_another": "🔁 വീണ്ടും പരിശോധിക്കൂ", "how_it_works": "❔ എങ്ങനെ പ്രവർത്തിക്കുന്നു"},
}

_CHECK_ANOTHER_PROMPT = {
    Language.en: "Sure - forward me the claim, image, or video you'd like checked.",
    Language.ml: "തീർച്ചയായും - പരിശോധിക്കേണ്ട അവകാശവാദം, ചിത്രം, അല്ലെങ്കിൽ വീഡിയോ ഫോർവേഡ് ചെയ്യൂ.",
}


# WhatsApp caps an interactive message's body at 1024 characters (a plain
# text message allows up to 4096) - a long explanation could exceed that, so
# _send_reply falls back to a plain text send rather than let the Graph API
# call fail outright.
_INTERACTIVE_BODY_MAX_LEN = 1024


async def _send_reply(providers: Providers, to: str, body: str, buttons: list) -> None:
    if len(body) > _INTERACTIVE_BODY_MAX_LEN:
        await providers.whatsapp.send_text_message(to, body)
        return
    await providers.whatsapp.send_interactive_buttons(to, body, buttons)


def _reply_buttons(language: Language) -> list:
    labels = _BUTTON_LABELS[language]
    return [
        InteractiveButton(id="check_another", title=labels["check_another"]),
        InteractiveButton(id="how_it_works", title=labels["how_it_works"]),
    ]


def _c2pa_image_line(image: Image, language: Language) -> Optional[str]:
    if not image.c2pa_has_manifest:
        return None
    # The service's own summary text is English-only for now (see
    # app.services.c2pa_service) - shown as-is even in a Malayalam reply
    # rather than silently dropped, since it's a materially stronger signal
    # than the perceptual line below it.
    return f"📎 {image.c2pa_summary}" if image.c2pa_summary else None


async def _build_reply_text(db: AsyncSession, verification: Verification, language: Language) -> str:
    if verification.verdict is None:
        # No verdict means the pipeline took its chitchat/unclear
        # short-circuit (see _short_circuit in app/agents/pipeline.py) - that
        # path already produces a plain, ready-to-send reply, so wrapping it
        # in the structured verdict template would show a nonsensical
        # "❓ UNVERIFIABLE - 0% confidence" for a greeting.
        return verification.explanation_text or ""

    image_lines = None
    if verification.has_image:
        image_result = await db.execute(select(Image).where(Image.verification_id == verification.id))
        image = image_result.scalar_one_or_none()
        if image is not None:
            image_lines = [
                line
                for line in (
                    _c2pa_image_line(image, language),
                    report_formatting.perceptual_image_line(image.ai_generated_probability, language),
                )
                if line
            ]

    return report_formatting.build_verdict_report(
        language=language,
        verdict=verification.verdict,
        confidence_score=verification.confidence_score,
        confidence_label=verification.confidence_label,
        claim_text=verification.claim_text,
        explanation_text=verification.explanation_text,
        image_lines=image_lines,
    )


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

    user, is_new_user = await verification_service.get_or_create_user(db, Channel.whatsapp, from_number, None)
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
        await _send_reply(providers, from_number, _WELCOME_TEXT[welcome_language], _reply_buttons(welcome_language))
        return

    message_type = message.get("type")

    if message_type == "interactive":
        # A tap on one of our own quick-reply buttons, not new content to
        # verify - answer it directly and don't run the verification
        # pipeline (there is no claim/image here to check).
        if message_id:
            await providers.whatsapp.mark_as_read(message_id)
        button_id = ((message.get("interactive") or {}).get("button_reply") or {}).get("id")
        button_language = user.preferred_language or Language.en
        if button_id == "how_it_works":
            await _send_reply(
                providers, from_number, _HOW_IT_WORKS_TEXT[button_language], _reply_buttons(button_language)
            )
        else:
            # Unrecognized button ids fall back to the same "go ahead and
            # forward something" prompt as "check_another" - there is no
            # third option to distinguish today.
            await providers.whatsapp.send_text_message(from_number, _CHECK_ANOTHER_PROMPT[button_language])
        return

    text: Optional[str] = None
    image_bytes: Optional[bytes] = None

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
    elif message_type == "video":
        video_field = message.get("video") or {}
        media_id = video_field.get("id")
        if media_id:
            video_bytes = await providers.whatsapp.download_media(media_id)
            # Best-effort: a representative frame feeds the existing
            # image-analysis pipeline (AI-generation detection, reverse
            # search), and the audio track feeds the existing speech-to-text
            # pipeline, same as a voice note - if ffmpeg can't decode it,
            # this degrades to just the caption rather than dropping the
            # message.
            image_bytes, video_audio_bytes = await video_processing.extract_frame_and_audio(video_bytes)
            transcript = None
            if video_audio_bytes:
                transcript = await providers.speech_to_text.transcribe(video_audio_bytes, mime_type="audio/mpeg")
            text = "\n".join(part for part in (video_field.get("caption"), transcript) if part) or None

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
    await _send_reply(
        providers,
        from_number,
        reply_text or "Sorry, I couldn't process that message.",
        _reply_buttons(reply_language),
    )


async def _detect_language(providers: Providers, text: Optional[str]) -> Optional[Language]:
    if not text or not text.strip():
        return None
    try:
        detected = await providers.translation.detect_language(text)
    except Exception:
        return None
    return _DETECTED_LANGUAGE_MAP.get(detected)

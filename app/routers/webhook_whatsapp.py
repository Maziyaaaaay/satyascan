from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.logging_conf import get_logger
from app.models.enums import Channel
from app.providers.bundle import Providers, build_providers
from app.security.signature import verify_signature
from app.services import verification_service
from app.services.rate_limit_service import RateLimitExceeded

router = APIRouter()
logger = get_logger(__name__)


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


async def _handle_message(message: dict, db: AsyncSession, providers: Providers) -> None:
    from_number = message.get("from")
    message_id = message.get("id")
    if from_number is None:
        return

    text: Optional[str] = None
    image_bytes: Optional[bytes] = None

    if message.get("type") == "text":
        text = (message.get("text") or {}).get("body")
    elif message.get("type") == "image":
        image_field = message.get("image") or {}
        media_id = image_field.get("id")
        if media_id:
            image_bytes = await providers.whatsapp.download_media(media_id)
        text = image_field.get("caption")

    try:
        verification = await verification_service.process_incoming(
            db,
            providers,
            channel=Channel.whatsapp,
            external_user_id=from_number,
            text=text,
            image_bytes=image_bytes,
            external_message_id=message_id,
        )
    except RateLimitExceeded:
        await providers.whatsapp.send_text_message(
            from_number, "You're sending messages too quickly - please wait a moment and try again."
        )
        return

    if message_id:
        await providers.whatsapp.mark_as_read(message_id)

    reply_text = verification.explanation_text or "Sorry, I couldn't process that message."
    await providers.whatsapp.send_text_message(from_number, reply_text)

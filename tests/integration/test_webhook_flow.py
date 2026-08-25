import os

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.base import get_session_factory
from app.models.verification import Verification


def _meta_text_message_payload(from_number: str, text: str, message_id: str = "wamid.TEST123"):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": message_id,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _meta_audio_message_payload(from_number: str, message_id: str = "wamid.AUDIO123"):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": message_id,
                                    "type": "audio",
                                    "audio": {"id": "media-id-1", "mime_type": "audio/ogg; codecs=opus"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_verify_challenge_succeeds_with_correct_token(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "correct-token")
    get_settings.cache_clear()

    response = await client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "correct-token", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_verify_challenge_rejects_wrong_token(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "correct-token")
    get_settings.cache_clear()

    response = await client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong-token", "hub.challenge": "12345"},
    )
    assert response.status_code == 403
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_inbound_text_message_creates_verification_and_sends_reply(app_client):
    client, providers = app_client
    payload = _meta_text_message_payload("+911234567890", "Drinking hot water cures COVID")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert len(verifications) == 1
    assert verifications[0].explanation_text

    assert len(providers.whatsapp.sent_messages) == 1
    assert providers.whatsapp.sent_messages[0]["to"] == "+911234567890"
    assert providers.whatsapp.sent_messages[0]["body"]
    assert providers.whatsapp.read_receipts == ["wamid.TEST123"]


@pytest.mark.asyncio
async def test_inbound_audio_message_is_transcribed_and_verified(app_client):
    client, providers = app_client
    payload = _meta_audio_message_payload("+911234567892")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert len(verifications) == 1
    # The mock speech-to-text provider returns a deterministic non-empty
    # transcript, which should have been run through the pipeline like any
    # typed claim - not silently dropped as an empty message.
    assert verifications[0].claim_text

    assert len(providers.whatsapp.sent_messages) == 1
    assert providers.whatsapp.read_receipts == ["wamid.AUDIO123"]


@pytest.mark.asyncio
async def test_signature_check_skipped_without_app_secret(app_client):
    client, _ = app_client
    assert os.environ.get("WHATSAPP_APP_SECRET") in (None, "")
    payload = _meta_text_message_payload("+911234567891", "hello")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

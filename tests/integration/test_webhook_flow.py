import os

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.base import get_session_factory
from app.models.enums import SourceMediaType
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


def _meta_video_message_payload(from_number: str, caption: str = "", message_id: str = "wamid.VIDEO123"):
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
                                    "type": "video",
                                    "video": {"id": "media-id-video-1", "mime_type": "video/mp4", "caption": caption},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _meta_interactive_button_payload(from_number: str, button_id: str, message_id: str = "wamid.BUTTON123"):
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
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": button_id, "title": "tapped"},
                                    },
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
async def test_first_ever_message_gets_welcome_text_and_no_verification(app_client):
    client, providers = app_client
    payload = _meta_text_message_payload("+911234567893", "hi", message_id="wamid.FIRST")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    # A brand-new user's first message should just get the welcome text -
    # the pipeline shouldn't run, and no Verification should be created.
    assert verifications == []

    assert len(providers.whatsapp.sent_messages) == 1
    assert "SatyaScan" in providers.whatsapp.sent_messages[0]["body"]
    assert providers.whatsapp.read_receipts == ["wamid.FIRST"]
    # The welcome message is sent as a native interactive (quick-reply
    # button) message, not plain text.
    assert providers.whatsapp.sent_messages[0]["buttons"]


@pytest.mark.asyncio
async def test_verdict_reply_is_sent_as_interactive_buttons(app_client):
    client, providers = app_client
    from_number = "+911234567898"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME898")
    await client.post("/webhook/whatsapp", json=priming_payload)

    payload = _meta_text_message_payload(from_number, "Drinking hot water cures COVID", message_id="wamid.BTN898")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    reply = providers.whatsapp.sent_messages[-1]
    assert reply["buttons"]
    button_ids = {button["id"] for button in reply["buttons"]}
    assert "check_another" in button_ids
    assert "how_it_works" in button_ids


@pytest.mark.asyncio
async def test_how_it_works_button_reply_sends_explainer(app_client):
    client, providers = app_client
    from_number = "+911234567899"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME899")
    await client.post("/webhook/whatsapp", json=priming_payload)

    payload = _meta_interactive_button_payload(from_number, "how_it_works", message_id="wamid.HOWITWORKS")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    reply = providers.whatsapp.sent_messages[-1]
    assert "How SatyaScan works" in reply["body"]
    assert providers.whatsapp.read_receipts[-1] == "wamid.HOWITWORKS"


@pytest.mark.asyncio
async def test_check_another_button_reply_does_not_run_pipeline(app_client):
    client, providers = app_client
    from_number = "+911234567800"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME800")
    await client.post("/webhook/whatsapp", json=priming_payload)

    payload = _meta_interactive_button_payload(from_number, "check_another", message_id="wamid.CHECKANOTHER")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert verifications == []

    reply = providers.whatsapp.sent_messages[-1]
    assert "forward" in reply["body"].lower()


@pytest.mark.asyncio
async def test_inbound_text_message_creates_verification_and_sends_reply(app_client):
    client, providers = app_client
    from_number = "+911234567890"
    # Prime the user: their very first message only gets the welcome text
    # (see test_first_ever_message_gets_welcome_text_and_no_verification) -
    # this test verifies normal, post-welcome behavior.
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME890")
    await client.post("/webhook/whatsapp", json=priming_payload)

    payload = _meta_text_message_payload(from_number, "Drinking hot water cures COVID")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert len(verifications) == 1
    assert verifications[0].explanation_text
    assert verifications[0].source_media_type == SourceMediaType.text

    assert len(providers.whatsapp.sent_messages) == 2
    assert providers.whatsapp.sent_messages[-1]["to"] == from_number
    assert providers.whatsapp.sent_messages[-1]["body"]
    assert providers.whatsapp.read_receipts == ["wamid.PRIME890", "wamid.TEST123"]


@pytest.mark.asyncio
async def test_inbound_audio_message_is_transcribed_and_verified(app_client):
    client, providers = app_client
    from_number = "+911234567892"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME892")
    await client.post("/webhook/whatsapp", json=priming_payload)

    payload = _meta_audio_message_payload(from_number)

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
    assert verifications[0].source_media_type == SourceMediaType.audio

    assert len(providers.whatsapp.sent_messages) == 2
    reply_body = providers.whatsapp.sent_messages[-1]["body"]
    # An audio message's reply must lead with the transcript, not a generic
    # "Claim:" line as if it were typed text.
    assert "What we heard" in reply_body
    assert "Claim:" not in reply_body


@pytest.mark.asyncio
async def test_inbound_audio_with_empty_transcript_asks_to_repeat(app_client, monkeypatch):
    # Regression test: silence/unintelligible audio used to proceed into
    # the full pipeline as an empty claim, landing on the generic
    # text-oriented "unclear" reply instead of an audio-appropriate
    # "couldn't catch that" prompt - and running a whole pipeline pass on
    # nothing at all.
    client, providers = app_client
    from_number = "+911234567895"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME895")
    await client.post("/webhook/whatsapp", json=priming_payload)

    async def empty_transcribe(audio_bytes, mime_type=None):
        return ""

    monkeypatch.setattr(providers.speech_to_text, "transcribe", empty_transcribe)

    payload = _meta_audio_message_payload(from_number, message_id="wamid.AUDIOEMPTY")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    # No verification should have been attempted on an empty transcript.
    assert verifications == []

    assert len(providers.whatsapp.sent_messages) == 2
    reply_body = providers.whatsapp.sent_messages[-1]["body"]
    assert "couldn't quite catch that" in reply_body
    assert providers.whatsapp.read_receipts[-1] == "wamid.AUDIOEMPTY"


@pytest.mark.asyncio
async def test_inbound_video_with_extraction_uses_frame_and_transcribed_audio(app_client, monkeypatch):
    client, providers = app_client
    from_number = "+911234567896"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME896")
    await client.post("/webhook/whatsapp", json=priming_payload)

    async def fake_extract(video_bytes: bytes):
        return b"fake-frame-bytes", b"fake-audio-bytes"

    monkeypatch.setattr("app.routers.webhook_whatsapp.video_processing.extract_frame_and_audio", fake_extract)

    payload = _meta_video_message_payload(from_number, caption="watch this")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert len(verifications) == 1
    # The extracted frame should have been threaded through as the
    # verification's image (claim_text itself may be reshaped by the mock
    # LLM's claim-extraction step, so just check it ran on non-empty input).
    assert verifications[0].has_image is True
    assert verifications[0].claim_text
    # This is the field the video-vs-photo report labeling actually keys
    # off (see report_formatting.build_verdict_report) - the exact reply
    # wording for each source_media_type is covered directly and
    # deterministically in tests/unit/services/test_report_formatting.py,
    # since the mock LLM's hash-derived intent classification can (rarely,
    # depending on the exact input) take the pipeline's chitchat/unclear
    # short-circuit instead of a full verdict, which would make a reply-text
    # assertion here flaky.
    assert verifications[0].source_media_type == SourceMediaType.video

    assert len(providers.whatsapp.sent_messages) == 2
    assert providers.whatsapp.read_receipts == ["wamid.PRIME896", "wamid.VIDEO123"]


@pytest.mark.asyncio
async def test_inbound_video_falls_back_to_caption_when_extraction_fails(app_client, monkeypatch):
    client, providers = app_client
    from_number = "+911234567897"
    priming_payload = _meta_text_message_payload(from_number, "hi", message_id="wamid.PRIME897")
    await client.post("/webhook/whatsapp", json=priming_payload)

    async def fake_extract(video_bytes: bytes):
        return None, None

    monkeypatch.setattr("app.routers.webhook_whatsapp.video_processing.extract_frame_and_audio", fake_extract)

    payload = _meta_video_message_payload(from_number, caption="Drinking hot water cures COVID")
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Verification))
        verifications = result.scalars().all()
    assert len(verifications) == 1
    assert verifications[0].has_image is False
    assert verifications[0].claim_text


@pytest.mark.asyncio
async def test_duplicate_webhook_delivery_only_replies_once(app_client):
    client, providers = app_client
    payload = _meta_text_message_payload("+911234567894", "hi", message_id="wamid.DUP")

    first = await client.post("/webhook/whatsapp", json=payload)
    second = await client.post("/webhook/whatsapp", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    # WhatsApp delivers webhooks at-least-once and retries on a slow
    # response - the retry (identical message id) must not trigger a
    # second reply.
    assert len(providers.whatsapp.sent_messages) == 1


@pytest.mark.asyncio
async def test_reply_with_no_verdict_is_not_wrapped_in_verdict_template():
    # Regression test for the pipeline's chitchat/unclear short-circuit (see
    # _short_circuit in app/agents/pipeline.py): it never sets a verdict, and
    # _build_reply_text must send its plain reply as-is instead of wrapping it
    # in "Verdict: UNVERIFIABLE / Confidence: 0/100", which reads as nonsense
    # for a greeting.
    from app.models.enums import Language
    from app.models.verification import Verification
    from app.routers.webhook_whatsapp import _build_reply_text

    verification = Verification(
        verdict=None,
        confidence_score=None,
        confidence_label=None,
        has_image=False,
        explanation_text="Hi! I'm SatyaScan. Forward me a message or image you'd like me to fact-check.",
    )

    reply = await _build_reply_text(db=None, verification=verification, language=Language.en)

    assert reply == verification.explanation_text
    assert "Verdict" not in reply
    assert "Confidence" not in reply


@pytest.mark.asyncio
async def test_signature_check_skipped_without_app_secret(app_client):
    client, _ = app_client
    assert os.environ.get("WHATSAPP_APP_SECRET") in (None, "")
    payload = _meta_text_message_payload("+911234567891", "hello")

    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200

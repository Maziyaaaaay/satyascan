import pytest

from app.providers.base import InteractiveButton, WhatsAppClient
from app.providers.whatsapp.mock import MockWhatsAppClient


@pytest.mark.asyncio
async def test_mock_whatsapp_is_a_whatsapp_client():
    assert isinstance(MockWhatsAppClient(), WhatsAppClient)


@pytest.mark.asyncio
async def test_send_text_message_records_and_returns_id():
    client = MockWhatsAppClient()
    message_id = await client.send_text_message(to="+911234567890", body="Verdict: False")
    assert message_id
    assert client.sent_messages == [{"to": "+911234567890", "body": "Verdict: False", "message_id": message_id}]


@pytest.mark.asyncio
async def test_send_interactive_buttons_records_body_and_buttons():
    client = MockWhatsAppClient()
    buttons = [InteractiveButton(id="check_another", title="🔁 Check another")]
    message_id = await client.send_interactive_buttons(to="+911234567890", body="Verdict text", buttons=buttons)
    assert message_id
    assert len(client.sent_messages) == 1
    sent = client.sent_messages[0]
    assert sent["to"] == "+911234567890"
    assert sent["body"] == "Verdict text"
    assert sent["buttons"] == [{"id": "check_another", "title": "🔁 Check another"}]


@pytest.mark.asyncio
async def test_download_media_returns_bytes():
    client = MockWhatsAppClient()
    data = await client.download_media("some-media-id")
    assert isinstance(data, bytes)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_mark_as_read_records_receipt():
    client = MockWhatsAppClient()
    await client.mark_as_read("wamid.123")
    assert client.read_receipts == ["wamid.123"]

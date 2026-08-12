import pytest

from app.providers.base import WhatsAppClient
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

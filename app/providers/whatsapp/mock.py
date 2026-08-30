import uuid
from typing import List

from app.providers.base import InteractiveButton, WhatsAppClient

_MOCK_IMAGE_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100e2266d0f0000000049454e44ae426082"
)


class MockWhatsAppClient(WhatsAppClient):
    """Records every outbound send so tests can assert on the reply that
    would have gone out over the real Meta Cloud API."""

    def __init__(self) -> None:
        self.sent_messages: List[dict] = []
        self.read_receipts: List[str] = []

    async def send_text_message(self, to: str, body: str) -> str:
        message_id = f"mock-wamid-{uuid.uuid4().hex[:16]}"
        self.sent_messages.append({"to": to, "body": body, "message_id": message_id})
        return message_id

    async def send_interactive_buttons(self, to: str, body: str, buttons: List[InteractiveButton]) -> str:
        message_id = f"mock-wamid-{uuid.uuid4().hex[:16]}"
        self.sent_messages.append(
            {
                "to": to,
                "body": body,
                "message_id": message_id,
                "buttons": [{"id": button.id, "title": button.title} for button in buttons],
            }
        )
        return message_id

    async def download_media(self, media_id: str) -> bytes:
        return _MOCK_IMAGE_BYTES

    async def mark_as_read(self, message_id: str) -> None:
        self.read_receipts.append(message_id)

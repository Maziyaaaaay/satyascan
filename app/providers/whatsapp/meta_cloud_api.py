import httpx

from app.providers.base import WhatsAppClient

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class MetaWhatsAppClient(WhatsAppClient):
    def __init__(self, access_token: str, phone_number_id: str):
        self._access_token = access_token
        self._phone_number_id = phone_number_id

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def send_text_message(self, to: str, body: str) -> str:
        url = f"{GRAPH_API_BASE}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            data = response.json()
        return data["messages"][0]["id"]

    async def download_media(self, media_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=15.0) as client:
            meta_response = await client.get(f"{GRAPH_API_BASE}/{media_id}", headers=self._headers)
            meta_response.raise_for_status()
            media_url = meta_response.json()["url"]

            media_response = await client.get(media_url, headers=self._headers)
            media_response.raise_for_status()
            return media_response.content

    async def mark_as_read(self, message_id: str) -> None:
        url = f"{GRAPH_API_BASE}/{self._phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()

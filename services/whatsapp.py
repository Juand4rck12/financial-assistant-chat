"""Cliente async para la API de WhatsApp Cloud API (Meta).

Basado en la coleccion oficial de Postman:
https://go.postman.co/collection/13382743-84d01ff8-4253-4720-b454-af661f36acc2
"""

from dataclasses import dataclass

import httpx

from core.config import settings

BASE_URL = "https://graph.facebook.com"


@dataclass
class TextMessage:
    """Estructura de un mensaje de texto saliente."""

    to: str
    body: str
    preview_url: bool = False


@dataclass
class MessageResponse:
    """Respuesta estandar de la API al enviar un mensaje."""

    id: str
    """ID del mensaje (prefijo wamid.*)."""


@dataclass
class WebhookMessage:
    """Mensaje entrante proveniente del webhook de WhatsApp."""

    from_: str
    """Numero de quien envia el mensaje."""

    id: str
    """ID del mensaje (wamid.*)."""

    timestamp: str
    """Timestamp Unix del mensaje."""

    type: str
    """Tipo de mensaje: text, audio, image, etc."""

    text_body: str | None = None
    """Contenido del texto (solo si type=text)."""


@dataclass
class WebhookPayload:
    """Payload completo del webhook entrante."""

    object: str
    entry: list["WebhookEntry"]


@dataclass
class WebhookEntry:
    id: str
    changes: list["WebhookChange"]


@dataclass
class WebhookChange:
    value: "WebhookValue"
    field: str


@dataclass
class WebhookValue:
    messaging_product: str
    metadata: dict
    contacts: list[dict] | None = None
    messages: list[dict] | None = None
    statuses: list[dict] | None = None


class WhatsAppClientError(Exception):
    """Error generico del cliente de WhatsApp."""


class WhatsAppClient:
    """Cliente async para la API de WhatsApp Cloud API de Meta.

    Metodos disponibles:
    - send_text: Envia un mensaje de texto.
    - mark_as_read: Marca un mensaje como leido.
    - subscribe_app: Suscribe la app al webhook de una WABA.
    - get_media_url: Obtiene la URL de descarga de un media.
    - download_media: Descarga un archivo media.
    """

    def __init__(
        self,
        token: str = "",
        phone_number_id: str = "",
        api_version: str = "",
    ) -> None:
        self._token = token or settings.whatsapp_token
        self._phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
        self._api_version = api_version or settings.whatsapp_api_version
        self._client = httpx.AsyncClient(
            base_url=f"{BASE_URL}/{self._api_version}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    async def send_text(self, message: TextMessage) -> MessageResponse:
        """Envia un mensaje de texto a un numero de WhatsApp.

        POST /{api-version}/{phone-number-id}/messages
        Ref: Postman collection → Messages → Send Text Message
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": message.to,
            "type": "text",
            "text": {
                "preview_url": message.preview_url,
                "body": message.body,
            },
        }
        response = await self._client.post(
            f"/{self._phone_number_id}/messages",
            json=payload,
        )
        if response.is_error:
            raise WhatsAppClientError(
                f"Error enviando mensaje: {response.status_code} - {response.text}"
            )
        data = response.json()
        return MessageResponse(id=data["messages"][0]["id"])

    async def mark_as_read(self, message_id: str) -> None:
        """Marca un mensaje entrante como leido.

        PUT /{api-version}/{phone-number-id}/messages
        Ref: Postman collection → Messages → Mark Message As Read
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        response = await self._client.post(
            f"/{self._phone_number_id}/messages",
            json=payload,
        )
        if response.is_error:
            raise WhatsAppClientError(
                f"Error marcando mensaje como leido: {response.status_code} - {response.text}"
            )

    async def subscribe_app(self) -> dict:
        """Suscribe la app a los eventos de la WABA.

        POST /{api-version}/{waba-id}/subscribed_apps
        Necesario para recibir webhooks.
        Ref: Postman collection → Webhook Subscriptions → Subscribe to a WABA
        """
        waba_id = settings.whatsapp_waba_id
        response = await self._client.post(f"/{waba_id}/subscribed_apps")
        if response.is_error:
            raise WhatsAppClientError(
                f"Error suscribiendo app: {response.status_code} - {response.text}"
            )
        return response.json()

    async def get_media_url(self, media_id: str) -> str:
        """Obtiene la URL de descarga de un media (imagen, audio, video).

        GET /{api-version}/{media-id}
        Ref: Postman collection → Media → Retrieve Media URL
        """
        response = await self._client.get(f"/{media_id}")
        if response.is_error:
            raise WhatsAppClientError(
                f"Error obteniendo media URL: {response.status_code} - {response.text}"
            )
        return response.json()["url"]

    async def download_media(self, media_url: str) -> bytes:
        """Descarga el contenido binario de un media usando su URL.

        La URL se obtiene con get_media_url().
        Ref: Postman collection → Media → Download Media
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        if response.is_error:
            raise WhatsAppClientError(
                f"Error descargando media: {response.status_code} - {response.text}"
            )
        return response.content

    async def close(self) -> None:
        await self._client.aclose()

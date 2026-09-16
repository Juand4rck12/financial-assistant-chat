"""Dependencias FastAPI para el modulo de WhatsApp.

Inyectan el cliente de WhatsApp y validan el webhook.
"""

from fastapi import HTTPException, Query, status

from core.config import settings
from services.whatsapp import WhatsAppClient


async def verify_webhook_token(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    """Valida el token de verificacion del webhook de WhatsApp.

    Meta envia un GET a /webhook con estos parametros al registrar el webhook.
    Si el verify_token coincide, devolvemos el challenge para confirmar.

    Retorna el challenge string si la verificacion es exitosa.
    Lanza HTTPException 403 si el token no coincide.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_webhook_verify_token:
        return hub_challenge or ""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed: verify_token mismatch",
    )


async def get_whatsapp_client() -> WhatsAppClient:
    """Inyecta una instancia del cliente de WhatsApp por request."""
    client = WhatsAppClient()
    try:
        yield client
    finally:
        await client.close()

"""Router de FastAPI para el webhook de WhatsApp Cloud API.

Endpoints:
    GET  /webhook  - Verificación del webhook (Meta challenge).
    POST /webhook  - Recepción de mensajes entrantes y conexión con LangGraph.
    POST /webhook/test - Endpoint de prueba para enviar mensajes salientes.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from api.whatsapp.dependencies import get_whatsapp_client, verify_webhook_token
from core.graph.builder import get_financial_graph
from services.whatsapp import TextMessage, WebhookMessage, WhatsAppClient
from services.whatsapp_formatter import format_whatsapp_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["whatsapp"])


# ── Modelos de entrada ─────────────────────────────────────────────

class TestMessageRequest(BaseModel):
    """Cuerpo del endpoint de prueba /test."""
    to: str
    message: str


# ── Endpoints del webhook ─────────────────────────────────────────

@router.get("", response_class=PlainTextResponse)
async def verify_webhook(challenge: str = Depends(verify_webhook_token)) -> str:
    """GET /webhook - Verificación del webhook de Meta.
    
    Devuelve el challenge como texto plano para validar la URL del webhook en Meta Developer Console.
    """
    return challenge


@router.post("")
async def receive_message(
    request: Request,
    client: WhatsAppClient = Depends(get_whatsapp_client),
):
    """POST /webhook - Recibe mensajes de WhatsApp y los enruta al orquestador LangGraph.
    
    1. Extrae remitente y texto del payload de Meta.
    2. Marca el mensaje como leído.
    3. Invoca el grafo multi-agente con thread_id = número del remitente.
    4. Limpia el texto de salida (sin markdown) y lo envía de vuelta al usuario.
    """
    body = await request.json()
    graph = get_financial_graph()

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            sender_name = contacts[0].get("profile", {}).get("name", "Usuario") if contacts else "Usuario"

            for msg in value.get("messages", []):
                webhook_msg = WebhookMessage(
                    from_=msg["from"],
                    id=msg["id"],
                    timestamp=msg["timestamp"],
                    type=msg["type"],
                    text_body=msg.get("text", {}).get("body") if msg["type"] == "text" else None,
                )

                logger.info(
                    "Mensaje de WhatsApp recibido de %s (%s): %s",
                    webhook_msg.from_,
                    sender_name,
                    webhook_msg.text_body or f"(tipo {webhook_msg.type})",
                )

                # 1. Marcar como leído en WhatsApp
                try:
                    await client.mark_as_read(webhook_msg.id)
                except Exception as err:
                    logger.warning("No se pudo marcar el mensaje como leído: %s", err)

                # 2. Si es mensaje de texto, procesarlo con el grafo LangGraph
                if webhook_msg.type == "text" and webhook_msg.text_body:
                    thread_id = webhook_msg.from_
                    graph_config = {"configurable": {"thread_id": thread_id}}

                    state_input = {
                        "messages": [HumanMessage(content=webhook_msg.text_body)],
                        "phone_number": webhook_msg.from_,
                        "user_name": sender_name,
                    }

                    try:
                        result = await graph.ainvoke(state_input, config=graph_config)
                        raw_reply = result.get(
                            "response_text",
                            "Disculpa, no pude procesar tu solicitud en este momento.",
                        )
                    except Exception as err:
                        logger.error("Error ejecutando el grafo de LangGraph: %s", err, exc_info=True)
                        raw_reply = "Ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo."

                    # 3. Formatear para WhatsApp (texto plano sin markdown)
                    clean_reply = format_whatsapp_text(raw_reply)

                    # 4. Enviar mensaje de vuelta vía WhatsApp API
                    reply_payload = TextMessage(to=webhook_msg.from_, body=clean_reply)
                    await client.send_text(reply_payload)

    return {"status": "ok"}


@router.post("/test")
async def send_test_message(
    payload: TestMessageRequest,
    client: WhatsAppClient = Depends(get_whatsapp_client),
):
    """POST /webhook/test - Envía un mensaje de prueba a un destinatario."""
    message = TextMessage(to=payload.to, body=payload.message)
    result = await client.send_text(message)
    return {"status": "sent", "message_id": result.id}

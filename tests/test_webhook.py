import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from main import app
from api.whatsapp.dependencies import get_whatsapp_client, verify_webhook_token
from services.whatsapp import MessageResponse


@pytest.fixture
def mock_whatsapp_client():
    client = AsyncMock()
    client.send_text.return_value = MessageResponse(id="wamid.mock123")
    client.mark_as_read.return_value = None
    return client


def test_verify_webhook_get(monkeypatch):
    """Test GET /webhook Meta challenge verification returns plain text."""
    app.dependency_overrides[verify_webhook_token] = lambda: "test_challenge_12345"
    client = TestClient(app)

    response = client.get("/webhook")
    assert response.status_code == 200
    assert response.text == "test_challenge_12345"
    assert "text/plain" in response.headers["content-type"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_receive_message_post(mock_whatsapp_client):
    """Test POST /webhook receives Meta payload and invokes LangGraph."""
    app.dependency_overrides[get_whatsapp_client] = lambda: mock_whatsapp_client
    client = TestClient(app)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                            "contacts": [{"profile": {"name": "Carlos"}, "wa_id": "573001234567"}],
                            "messages": [
                                {
                                    "from": "573001234567",
                                    "id": "wamid.HBgL...",
                                    "timestamp": "1726000000",
                                    "text": {"body": "Gasté 35000 en gasolina"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verificar que mark_as_read fue llamado
    mock_whatsapp_client.mark_as_read.assert_awaited_once()

    # Verificar que send_text fue llamado con la respuesta formateada
    mock_whatsapp_client.send_text.assert_awaited_once()
    sent_msg = mock_whatsapp_client.send_text.call_args[0][0]
    assert sent_msg.to == "573001234567"
    assert "35.000 COP" in sent_msg.body
    assert "Responde Sí o No" in sent_msg.body

    app.dependency_overrides.clear()

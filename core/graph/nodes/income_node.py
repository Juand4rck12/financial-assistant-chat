import logging
import uuid
from datetime import date
from decimal import Decimal

from core.graph.state import AgentState
from core.tools.calculator_tool import format_currency_cop, to_decimal
from core.tools.db_tool import create_income
from db.connection import get_session_factory

logger = logging.getLogger(__name__)


async def income_node(state: AgentState) -> dict:
    """Handle income registration with strict 'collect before write' confirmation."""
    pending = state.get("pending_action") or {}
    awaiting = state.get("awaiting_confirmation", False)

    messages = state.get("messages", [])
    last_msg = messages[-1].content.strip().lower() if messages else ""

    # ── 1. Ciclo de confirmación activa ───────────────────────────────
    if awaiting and pending.get("type") == "income":
        if any(word in last_msg for word in ["sí", "si", "confirmo", "dale", "ok", "correcto", "yes", "claro"]):
            amount = pending["amount"]
            source = pending.get("source", "Ingreso General")
            description = pending.get("description", source)
            tx_date = pending.get("date") or date.today()

            user_id = uuid.UUID(state["user_id"]) if state.get("user_id") else uuid.uuid4()
            account_id = uuid.UUID(pending["account_id"]) if pending.get("account_id") else None

            session_factory = get_session_factory()
            async with session_factory() as session:
                await create_income(
                    session=session,
                    user_id=user_id,
                    amount=amount,
                    source=source,
                    description=description,
                    transaction_date=tx_date,
                    account_id=account_id,
                )

            formatted_amt = format_currency_cop(amount)
            msg = f"✅ Registrado con éxito: Ingreso de {formatted_amt} por concepto de {source}."
            return {
                "response_text": msg,
                "pending_action": None,
                "awaiting_confirmation": False,
                "active_intent": None,
            }

        if any(word in last_msg for word in ["no", "cancela", "cancelar", "no gracias", "dejalo"]):
            return {
                "response_text": "❌ Registro cancelado. No se guardó ningún ingreso. ¿En qué más puedo orientarte?",
                "pending_action": None,
                "awaiting_confirmation": False,
                "active_intent": None,
            }

        formatted_amt = format_currency_cop(pending["amount"])
        return {
            "response_text": f"Tengo pendiente registrar un ingreso de {formatted_amt} ({pending.get('source')}). ¿Deseas confirmarlo? Responde Sí o No.",
            "awaiting_confirmation": True,
        }

    # ── 2. Validación de campos obligatorios ──────────────────────────
    amount = pending.get("amount")
    if not amount or to_decimal(amount) <= Decimal("0.00"):
        return {
            "response_text": "¿Cuál fue el valor exacto del ingreso en pesos (COP)?",
            "pending_action": pending,
            "awaiting_confirmation": False,
        }

    source = pending.get("source")
    if not source:
        return {
            "response_text": "¿Cuál es la fuente u origen de este ingreso? (Por ejemplo: Salario, Freelance, Rendimientos)",
            "pending_action": pending,
            "awaiting_confirmation": False,
        }

    description = pending.get("description", source)

    # ── 3. Solicitud de confirmación explícita ─────────────────────────
    formatted_amt = format_currency_cop(amount)
    confirm_msg = f"¿Confirmas registrar un ingreso de {formatted_amt} de {source} ({description})? Responde Sí o No."

    return {
        "response_text": confirm_msg,
        "pending_action": {
            "type": "income",
            "amount": amount,
            "source": source,
            "description": description,
            "date": pending.get("date", date.today()),
            "account_id": pending.get("account_id"),
        },
        "awaiting_confirmation": True,
        "active_intent": "income",
    }

import logging
import uuid
from datetime import date
from decimal import Decimal

from core.graph.state import AgentState
from core.tools.calculator_tool import format_currency_cop, to_decimal
from core.tools.db_tool import create_expense
from db.connection import get_session_factory

logger = logging.getLogger(__name__)


async def expense_node(state: AgentState) -> dict:
    """Handle expense creation with strict 'collect before write' confirmation."""
    pending = state.get("pending_action") or {}
    awaiting = state.get("awaiting_confirmation", False)

    # Obtenemos el último mensaje del usuario
    messages = state.get("messages", [])
    last_msg = messages[-1].content.strip().lower() if messages else ""

    # ── 1. Ciclo de confirmación activa ───────────────────────────────
    if awaiting and pending.get("type") == "expense":
        # Palabras afirmativas
        if any(word in last_msg for word in ["sí", "si", "confirmo", "dale", "ok", "correcto", "yes", "claro"]):
            amount = pending["amount"]
            category = pending.get("category", "Varios")
            description = pending.get("description", category)
            tx_date = pending.get("date") or date.today()

            user_id = uuid.UUID(state["user_id"]) if state.get("user_id") else uuid.uuid4()
            account_id = uuid.UUID(pending["account_id"]) if pending.get("account_id") else None

            session_factory = get_session_factory()
            async with session_factory() as session:
                await create_expense(
                    session=session,
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    description=description,
                    transaction_date=tx_date,
                    account_id=account_id,
                )

            formatted_amt = format_currency_cop(amount)
            msg = f"✅ Registrado con éxito: Gasto de {formatted_amt} en {category} ({description})."
            return {
                "response_text": msg,
                "pending_action": None,
                "awaiting_confirmation": False,
                "active_intent": None,
            }

        # Palabras negativas o de cancelación
        if any(word in last_msg for word in ["no", "cancela", "cancelar", "no gracias", "dejalo"]):
            return {
                "response_text": "❌ Registro cancelado. No se guardó ningún gasto. ¿En qué más te puedo ayudar?",
                "pending_action": None,
                "awaiting_confirmation": False,
                "active_intent": None,
            }

        # Si el usuario responde algo ambiguo durante la confirmación
        formatted_amt = format_currency_cop(pending["amount"])
        return {
            "response_text": f"Tengo pendiente registrar un gasto de {formatted_amt} en {pending.get('category')}. ¿Deseas confirmarlo? Responde Sí o No.",
            "awaiting_confirmation": True,
        }

    # ── 2. Validación de campos obligatorios ──────────────────────────
    amount = pending.get("amount")
    if not amount or to_decimal(amount) <= Decimal("0.00"):
        return {
            "response_text": "¿Cuál fue el valor exacto del gasto en pesos (COP)?",
            "pending_action": pending,
            "awaiting_confirmation": False,
        }

    category = pending.get("category")
    if not category:
        return {
            "response_text": "¿En qué categoría clasificarías este gasto? (Por ejemplo: Alimentación, Transporte, Servicios, Ocio)",
            "pending_action": pending,
            "awaiting_confirmation": False,
        }

    description = pending.get("description", category)

    # ── 3. Solicitud de confirmación explícita (Collect before write) ──
    formatted_amt = format_currency_cop(amount)
    confirm_msg = f"¿Confirmas registrar un gasto de {formatted_amt} en {category} ({description})? Responde Sí o No."

    return {
        "response_text": confirm_msg,
        "pending_action": {
            "type": "expense",
            "amount": amount,
            "category": category,
            "description": description,
            "date": pending.get("date", date.today()),
            "account_id": pending.get("account_id"),
        },
        "awaiting_confirmation": True,
        "active_intent": "expense",
    }

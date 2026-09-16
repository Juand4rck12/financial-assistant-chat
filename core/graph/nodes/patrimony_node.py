import logging
import uuid

from core.graph.state import AgentState
from core.tools.calculator_tool import format_currency_cop
from core.tools.db_tool import get_net_worth_summary
from db.connection import get_session_factory

logger = logging.getLogger(__name__)


async def patrimony_node(state: AgentState) -> dict:
    """Query accounts, debts and calculate net worth deterministically via SQL."""
    user_id_raw = state.get("user_id")
    if not user_id_raw:
        return {
            "response_text": "No encontré tu perfil de usuario para consultar el patrimonio.",
            "active_intent": None,
        }

    user_id = uuid.UUID(user_id_raw)
    session_factory = get_session_factory()
    async with session_factory() as session:
        summary = await get_net_worth_summary(session, user_id=user_id)

    lines = [
        "📊 Tu Patrimonio Neto Actual:",
        f"Patrimonio Neto: {format_currency_cop(summary.net_worth)}",
        f"Total Activos: {format_currency_cop(summary.total_assets)}",
        f"Total Pasivos (Deudas): {format_currency_cop(summary.total_liabilities)}",
        "",
    ]

    if summary.accounts:
        lines.append("Cuentas y Activos:")
        for idx, acc in enumerate(summary.accounts, start=1):
            lines.append(f"{idx}. {acc.name}: {format_currency_cop(acc.current_balance)}")
        lines.append("")
    else:
        lines.append("No tienes cuentas registradas aún.")
        lines.append("")

    if summary.liabilities:
        lines.append("Deudas y Pasivos:")
        for idx, liab in enumerate(summary.liabilities, start=1):
            lines.append(f"{idx}. {liab.name}: {format_currency_cop(liab.current_balance)}")
    else:
        lines.append("No tienes deudas registradas actualmente. ¡Excelente!")

    return {
        "response_text": "\n".join(lines),
        "active_intent": None,
        "awaiting_confirmation": False,
    }

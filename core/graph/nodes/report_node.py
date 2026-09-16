import logging
import uuid

from core.graph.state import AgentState
from core.tools.calculator_tool import format_currency_cop
from core.tools.date_utils import get_period_date_range
from core.tools.db_tool import get_financial_summary
from db.connection import get_session_factory

logger = logging.getLogger(__name__)


async def report_node(state: AgentState) -> dict:
    """Generate financial summaries and category breakdown deterministically via SQL."""
    user_id_raw = state.get("user_id")
    if not user_id_raw:
        return {
            "response_text": "No se pudo identificar tu usuario para generar el reporte.",
            "active_intent": None,
        }

    user_id = uuid.UUID(user_id_raw)
    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""

    # Determinar el rango de fechas con cálculo matemático determinista
    start_date, end_date, label = get_period_date_range(last_msg)

    session_factory = get_session_factory()
    async with session_factory() as session:
        summary = await get_financial_summary(
            session=session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

    lines = [
        f"📈 Resumen Financiero ({label}):",
        f"Periodo: {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}",
        "",
        f"Ingresos: {format_currency_cop(summary.total_income)}",
        f"Gastos: {format_currency_cop(summary.total_expense)}",
        f"Ahorro Neto: {format_currency_cop(summary.net_savings)} (Tasa de ahorro: {summary.savings_rate_percentage}%)",
        "",
    ]

    if summary.categories_breakdown:
        lines.append("Gastos por categoría:")
        for idx, cat in enumerate(summary.categories_breakdown, start=1):
            formatted_cat_amt = format_currency_cop(cat.total_amount)
            lines.append(f"{idx}. {cat.category}: {formatted_cat_amt} ({cat.percentage}%, {cat.transaction_count} movs)")
    else:
        lines.append("No se registraron gastos en este periodo.")

    return {
        "response_text": "\n".join(lines),
        "active_intent": None,
        "awaiting_confirmation": False,
    }

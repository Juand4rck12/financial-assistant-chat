import pytest
from decimal import Decimal
from langchain_core.messages import HumanMessage

import db.connection as db_conn
from db.models import AccountType
from core.graph.builder import build_financial_graph
from core.tools.db_tool import create_account, get_or_create_user


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Ensure all database tables exist before running node tests."""
    await db_conn.init_db()


@pytest.mark.asyncio
async def test_expense_confirmation_flow():
    """Verify strict two-turn 'collect before write' confirmation for expense."""
    graph = build_financial_graph()
    phone = "+573001239999"
    config = {"configurable": {"thread_id": phone}}

    # ── Turno 1: Usuario anuncia un gasto ──────────────────────────────
    input_turn_1 = {
        "messages": [HumanMessage(content="Gasté 45000 en almuerzo")],
        "phone_number": phone,
        "user_name": "Mateo",
    }
    output_turn_1 = await graph.ainvoke(input_turn_1, config=config)

    assert output_turn_1["awaiting_confirmation"] is True
    assert output_turn_1["pending_action"]["amount"] == Decimal("45000")
    assert output_turn_1["pending_action"]["category"] == "Alimentación"
    assert "45.000 COP" in output_turn_1["response_text"]
    assert "Responde Sí o No" in output_turn_1["response_text"]

    # ── Turno 2: Usuario confirma con 'Sí' ─────────────────────────────
    input_turn_2 = {
        "messages": [HumanMessage(content="Sí, confirmo")],
        "phone_number": phone,
        "user_name": "Mateo",
    }
    output_turn_2 = await graph.ainvoke(input_turn_2, config=config)

    assert output_turn_2["awaiting_confirmation"] is False
    assert output_turn_2["pending_action"] is None
    assert "Registrado con éxito" in output_turn_2["response_text"]
    assert "45.000 COP" in output_turn_2["response_text"]


@pytest.mark.asyncio
async def test_expense_cancellation_flow():
    """Verify user can cancel a pending expense."""
    graph = build_financial_graph()
    phone = "+573007778888"
    config = {"configurable": {"thread_id": phone}}

    # Turno 1: Anuncio de gasto
    await graph.ainvoke(
        {
            "messages": [HumanMessage(content="Pagué 120000 en compras")],
            "phone_number": phone,
            "user_name": "Lucía",
        },
        config=config,
    )

    # Turno 2: Usuario dice 'No'
    output_turn_2 = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="No, cancela eso")],
            "phone_number": phone,
            "user_name": "Lucía",
        },
        config=config,
    )

    assert output_turn_2["awaiting_confirmation"] is False
    assert output_turn_2["pending_action"] is None
    assert "Registro cancelado" in output_turn_2["response_text"]


@pytest.mark.asyncio
async def test_patrimony_inquiry_flow():
    """Verify user can query net worth and accounts."""
    graph = build_financial_graph()
    phone = "+573004443322"
    config = {"configurable": {"thread_id": phone}}

    session_factory = db_conn.get_session_factory()
    async with session_factory() as session:
        user = await get_or_create_user(session, phone, "Pedro")
        await create_account(
            session,
            user_id=user.id,
            name="Bancolombia",
            account_type=AccountType.SAVINGS,
            initial_balance=Decimal("3500000.00"),
        )

    output = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="¿Cuál es mi patrimonio actual y mis cuentas?")],
            "phone_number": phone,
            "user_name": "Pedro",
        },
        config=config,
    )

    assert "Tu Patrimonio Neto Actual" in output["response_text"]
    assert "3.500.000 COP" in output["response_text"]
    assert "Bancolombia" in output["response_text"]


@pytest.mark.asyncio
async def test_report_inquiry_flow():
    """Verify user can query period report."""
    graph = build_financial_graph()
    phone = "+573006665544"
    config = {"configurable": {"thread_id": phone}}

    output = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="¿Cuánto he gastado este mes?")],
            "phone_number": phone,
            "user_name": "Camila",
        },
        config=config,
    )

    assert "Resumen Financiero" in output["response_text"]
    assert "Ingresos:" in output["response_text"]
    assert "Gastos:" in output["response_text"]

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models import AccountType, LiabilityType, User
from core.tools.db_tool import (
    create_account,
    create_expense,
    create_income,
    create_liability,
    get_financial_summary,
    get_net_worth_summary,
    get_or_create_user,
)


@pytest.fixture
async def async_session():
    """Create a temporary in-memory async SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_user(async_session: AsyncSession):
    user = await get_or_create_user(async_session, phone_number="+573001234567", name="Juan")
    assert user.phone_number == "+573001234567"
    assert user.name == "Juan"

    # Idempotente: si vuelve a llamar, debe retornar el mismo usuario
    user_same = await get_or_create_user(async_session, phone_number="+573001234567")
    assert user_same.id == user.id


@pytest.mark.asyncio
async def test_create_expense_and_account_deduction(async_session: AsyncSession):
    user = await get_or_create_user(async_session, "+573001112233", "Carlos")
    
    # Crear cuenta con saldo inicial de 100.000 COP
    account = await create_account(
        async_session,
        user_id=user.id,
        name="Bancolombia Ahorros",
        account_type=AccountType.SAVINGS,
        initial_balance=Decimal("100000.00"),
    )
    assert account.current_balance == Decimal("100000.00")

    # Registrar gasto de 25.000 COP vinculado a la cuenta
    expense = await create_expense(
        async_session,
        user_id=user.id,
        amount=Decimal("25000.00"),
        category="Alimentación",
        description="Almuerzo ejecutivo",
        transaction_date=date(2026, 9, 16),
        account_id=account.id,
    )
    assert expense.amount == Decimal("25000.00")

    # Saldo de cuenta debe haber disminuido automáticamente a 75.000 COP
    await async_session.refresh(account)
    assert account.current_balance == Decimal("75000.00")


@pytest.mark.asyncio
async def test_financial_summary_aggregations(async_session: AsyncSession):
    user = await get_or_create_user(async_session, "+573009998877", "Diana")
    today = date(2026, 9, 16)

    # Registrar ingresos
    await create_income(
        async_session,
        user_id=user.id,
        amount=Decimal("3000000.00"),
        source="Salario",
        description="Nómina quincenal",
        transaction_date=today,
    )

    # Registrar gastos
    await create_expense(
        async_session,
        user_id=user.id,
        amount=Decimal("150000.00"),
        category="Servicios",
        description="Recibo de luz",
        transaction_date=today,
    )
    await create_expense(
        async_session,
        user_id=user.id,
        amount=Decimal("50000.00"),
        category="Alimentación",
        description="Supermercado",
        transaction_date=today,
    )

    summary = await get_financial_summary(
        async_session,
        user_id=user.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )

    assert summary.total_income == Decimal("3000000.00")
    assert summary.total_expense == Decimal("200000.00")
    assert summary.net_savings == Decimal("2800000.00")
    assert len(summary.categories_breakdown) == 2
    assert summary.categories_breakdown[0].category == "Servicios"
    assert summary.categories_breakdown[0].total_amount == Decimal("150000.00")


@pytest.mark.asyncio
async def test_get_net_worth_summary(async_session: AsyncSession):
    user = await get_or_create_user(async_session, "+573005554433", "Andrés")

    # Activos: 2.000.000 en banco + 500.000 en efectivo
    await create_account(
        async_session,
        user_id=user.id,
        name="Nu Cuenta",
        account_type=AccountType.SAVINGS,
        initial_balance=Decimal("2000000.00"),
    )
    await create_account(
        async_session,
        user_id=user.id,
        name="Efectivo",
        account_type=AccountType.CASH,
        initial_balance=Decimal("500000.00"),
    )

    # Pasivo: 700.000 en tarjeta
    await create_liability(
        async_session,
        user_id=user.id,
        name="Tarjeta Nu",
        liability_type=LiabilityType.CREDIT_CARD,
        current_balance=Decimal("700000.00"),
    )

    net_worth_res = await get_net_worth_summary(async_session, user_id=user.id)
    assert net_worth_res.total_assets == Decimal("2500000.00")
    assert net_worth_res.total_liabilities == Decimal("700000.00")
    assert net_worth_res.net_worth == Decimal("1800000.00")

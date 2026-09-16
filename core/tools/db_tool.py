import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.schemas import (
    AccountRead,
    CategorySummary,
    FinancialPeriodSummary,
    LiabilityRead,
    NetWorthSummary,
)
from core.tools.calculator_tool import (
    calculate_net_worth,
    calculate_percentage,
    calculate_period_balance,
    calculate_savings_rate,
    to_decimal,
)
from db.models import (
    Account,
    AccountType,
    Expense,
    ExpenseType,
    Income,
    IncomeType,
    Liability,
    LiabilityType,
    User,
)

logger = logging.getLogger(__name__)


# ── User Operations ───────────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession, phone_number: str, name: str = "Usuario"
) -> User:
    """Retrieve existing user by WhatsApp phone number or create a new one."""
    stmt = select(User).where(User.phone_number == phone_number)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            phone_number=phone_number,
            name=name,
            base_currency="COP",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Created new user: %s (%s)", user.name, user.phone_number)
    return user


# ── Expense Operations ────────────────────────────────────────────────

async def create_expense(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: Decimal | float | int | str,
    category: str,
    description: str,
    transaction_date: date,
    account_id: Optional[uuid.UUID] = None,
    expense_type: ExpenseType = ExpenseType.VARIABLE,
    statement_id: Optional[uuid.UUID] = None,
) -> Expense:
    """Register a new expense and optionally update the source account balance."""
    dec_amount = to_decimal(amount)

    expense = Expense(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        category=category.strip().title(),
        description=description.strip(),
        amount=dec_amount,
        date=transaction_date,
        expense_type=expense_type,
        statement_id=statement_id,
    )
    session.add(expense)

    # Si se asocia a una cuenta, descontar el saldo automáticamente de forma determinista
    if account_id:
        acc_stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        acc_res = await session.execute(acc_stmt)
        account = acc_res.scalar_one_or_none()
        if account:
            account.current_balance = (account.current_balance - dec_amount).quantize(Decimal("0.01"))

    await session.commit()
    await session.refresh(expense)
    return expense


# ── Income Operations ─────────────────────────────────────────────────

async def create_income(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: Decimal | float | int | str,
    source: str,
    description: Optional[str],
    transaction_date: date,
    account_id: Optional[uuid.UUID] = None,
    income_type: IncomeType = IncomeType.ACTUAL,
    statement_id: Optional[uuid.UUID] = None,
) -> Income:
    """Register a new income and optionally credit the target account balance."""
    dec_amount = to_decimal(amount)

    income = Income(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        source=source.strip().title(),
        description=description.strip() if description else None,
        amount=dec_amount,
        date=transaction_date,
        income_type=income_type,
        statement_id=statement_id,
    )
    session.add(income)

    # Si se asocia a una cuenta, sumar el saldo automáticamente de forma determinista
    if account_id:
        acc_stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        acc_res = await session.execute(acc_stmt)
        account = acc_res.scalar_one_or_none()
        if account:
            account.current_balance = (account.current_balance + dec_amount).quantize(Decimal("0.01"))

    await session.commit()
    await session.refresh(income)
    return income


# ── Account / Net Worth Operations ────────────────────────────────────

async def create_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    account_type: AccountType = AccountType.SAVINGS,
    initial_balance: Decimal | float | int | str = Decimal("0.00"),
    institution: Optional[str] = None,
) -> Account:
    """Create a new financial account (asset)."""
    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name.strip(),
        account_type=account_type,
        current_balance=to_decimal(initial_balance),
        currency="COP",
        institution=institution.strip() if institution else None,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def create_liability(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    liability_type: LiabilityType = LiabilityType.CREDIT_CARD,
    current_balance: Decimal | float | int | str = Decimal("0.00"),
    interest_rate: Optional[Decimal] = None,
    due_date: Optional[date] = None,
) -> Liability:
    """Register a new debt/liability."""
    liability = Liability(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name.strip(),
        liability_type=liability_type,
        current_balance=to_decimal(current_balance),
        interest_rate=interest_rate,
        due_date=due_date,
    )
    session.add(liability)
    await session.commit()
    await session.refresh(liability)
    return liability


async def get_net_worth_summary(
    session: AsyncSession, user_id: uuid.UUID
) -> NetWorthSummary:
    """Calculate net worth deterministically from active accounts and liabilities.
    
    Patrimonio Neto = Suma(Activos) - Suma(Pasivos)
    """
    # 1. Obtener todas las cuentas activas
    acc_stmt = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
    acc_res = await session.execute(acc_stmt)
    accounts = list(acc_res.scalars().all())

    # 2. Obtener todos los pasivos vigentes
    liab_stmt = select(Liability).where(Liability.user_id == user_id)
    liab_res = await session.execute(liab_stmt)
    liabilities = list(liab_res.scalars().all())

    # 3. Cálculo determinista mediante calculator_tool
    total_assets, total_liab, net_worth = calculate_net_worth(
        asset_balances=[a.current_balance for a in accounts],
        liability_balances=[l.current_balance for l in liabilities],
    )

    return NetWorthSummary(
        total_assets=total_assets,
        total_liabilities=total_liab,
        net_worth=net_worth,
        currency="COP",
        accounts=[AccountRead.model_validate(a) for a in accounts],
        liabilities=[LiabilityRead.model_validate(l) for l in liabilities],
    )


# ── Aggregated Reporting Operations (SQL Pure Calculations) ───────────

async def get_financial_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> FinancialPeriodSummary:
    """Compute financial summary for a period entirely via SQL aggregations.
    
    No hay alucinación del LLM: PostgreSQL suma y agrupa los registros directamente.
    """
    # 1. Total Gastos en el periodo
    exp_sum_stmt = select(func.coalesce(func.sum(Expense.amount), Decimal("0.00"))).where(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date,
    )
    exp_res = await session.execute(exp_sum_stmt)
    total_expense = to_decimal(exp_res.scalar_one())

    # 2. Total Ingresos en el periodo
    inc_sum_stmt = select(func.coalesce(func.sum(Income.amount), Decimal("0.00"))).where(
        Income.user_id == user_id,
        Income.date >= start_date,
        Income.date <= end_date,
    )
    inc_res = await session.execute(inc_sum_stmt)
    total_income = to_decimal(inc_res.scalar_one())

    # 3. Desglose de Gastos por Categoría con conteo y suma
    cat_stmt = (
        select(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("cat_total"),
            func.count(Expense.id).label("tx_count"),
        )
        .where(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    )
    cat_res = await session.execute(cat_stmt)

    categories_breakdown: List[CategorySummary] = []
    for cat_name, cat_total_raw, tx_count in cat_res.all():
        cat_total = to_decimal(cat_total_raw)
        pct = calculate_percentage(cat_total, total_expense)
        categories_breakdown.append(
            CategorySummary(
                category=cat_name,
                total_amount=cat_total,
                transaction_count=tx_count,
                percentage=pct,
            )
        )

    # 4. Ahorro neto y tasa de ahorro calculados con funciones deterministas
    net_savings = calculate_period_balance(total_income, total_expense)
    savings_rate = calculate_savings_rate(total_income, total_expense)

    return FinancialPeriodSummary(
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_expense=total_expense,
        net_savings=net_savings,
        savings_rate_percentage=savings_rate,
        categories_breakdown=categories_breakdown,
    )


async def get_recent_transactions(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 5
) -> List[dict]:
    """Fetch the most recent expenses and incomes for quick user overview."""
    exp_stmt = (
        select(Expense)
        .where(Expense.user_id == user_id)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(limit)
    )
    exp_res = await session.execute(exp_stmt)
    expenses = exp_res.scalars().all()

    txs = []
    for e in expenses:
        txs.append({
            "type": "gasto",
            "amount": e.amount,
            "category": e.category,
            "description": e.description,
            "date": e.date,
        })
    return txs

import uuid
from datetime import date as dt_date, datetime as dt_datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from db.models import (
    AccountType,
    CategoryType,
    ExpenseType,
    IncomeType,
    LiabilityType,
    StatementStatus,
)


# ── User Schemas ──────────────────────────────────────────────────────

class UserBase(BaseModel):
    phone_number: str = Field(..., description="WhatsApp phone number with country code")
    name: str = Field(..., description="User's display or full name")
    email: Optional[str] = Field(None, description="Optional email address for web access")
    base_currency: str = Field("COP", description="Default ISO currency code")


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: uuid.UUID
    created_at: dt_datetime
    updated_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


# ── Account Schemas (Assets) ──────────────────────────────────────────

class AccountBase(BaseModel):
    name: str = Field(..., description="Account name (e.g., Bancolombia Ahorros, Nu, Efectivo)")
    account_type: AccountType = Field(default=AccountType.SAVINGS)
    current_balance: Decimal = Field(default=Decimal("0.00"), description="Current balance in COP")
    currency: str = Field(default="COP")
    institution: Optional[str] = Field(None, description="Bank or entity name")
    is_active: bool = Field(default=True)


class AccountCreate(AccountBase):
    user_id: uuid.UUID


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    current_balance: Optional[Decimal] = None
    is_active: Optional[bool] = None


class AccountRead(AccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt_datetime
    updated_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


# ── Liability Schemas (Debts) ─────────────────────────────────────────

class LiabilityBase(BaseModel):
    name: str = Field(..., description="Debt name (e.g., Tarjeta Crédito Nu, Crédito Libre Inversión)")
    liability_type: LiabilityType = Field(default=LiabilityType.CREDIT_CARD)
    current_balance: Decimal = Field(default=Decimal("0.00"), description="Outstanding debt balance")
    interest_rate: Optional[Decimal] = Field(None, description="Annual percentage interest rate")
    due_date: Optional[dt_date] = Field(None, description="Payment deadline or due date")


class LiabilityCreate(LiabilityBase):
    user_id: uuid.UUID


class LiabilityUpdate(BaseModel):
    name: Optional[str] = None
    current_balance: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    due_date: Optional[dt_date] = None


class LiabilityRead(LiabilityBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt_datetime
    updated_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


# ── Category Schemas ──────────────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str = Field(..., description="Category name (e.g., Alimentación, Transporte)")
    category_type: CategoryType = Field(default=CategoryType.EXPENSE)
    icon: Optional[str] = Field(None, description="Emoji or icon representation")
    is_default: bool = Field(default=False)


class CategoryCreate(CategoryBase):
    user_id: Optional[uuid.UUID] = None


class CategoryRead(CategoryBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


# ── Expense Schemas ───────────────────────────────────────────────────

class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Expense amount in COP")
    category: str = Field(..., description="Category name")
    description: str = Field(..., description="Brief description of the expense")
    date: dt_date = Field(..., description="Date of transaction")
    expense_type: ExpenseType = Field(default=ExpenseType.VARIABLE)
    account_id: Optional[uuid.UUID] = Field(None, description="Account from which money was spent")
    category_id: Optional[uuid.UUID] = None


class ExpenseCreate(ExpenseBase):
    user_id: uuid.UUID
    statement_id: Optional[uuid.UUID] = None


class ExpenseRead(ExpenseBase):
    id: uuid.UUID
    user_id: uuid.UUID
    statement_id: Optional[uuid.UUID] = None
    created_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseFilter(BaseModel):
    user_id: uuid.UUID
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    category: Optional[str] = None
    account_id: Optional[uuid.UUID] = None


# ── Income Schemas ────────────────────────────────────────────────────

class IncomeBase(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Income amount in COP")
    source: str = Field(..., description="Income source (e.g., Salario, Freelance, Rendimientos)")
    description: Optional[str] = Field(None, description="Additional details")
    date: dt_date = Field(..., description="Date of income")
    income_type: IncomeType = Field(default=IncomeType.ACTUAL)
    account_id: Optional[uuid.UUID] = Field(None, description="Account where money was received")
    category_id: Optional[uuid.UUID] = None


class IncomeCreate(IncomeBase):
    user_id: uuid.UUID
    statement_id: Optional[uuid.UUID] = None


class IncomeRead(IncomeBase):
    id: uuid.UUID
    user_id: uuid.UUID
    statement_id: Optional[uuid.UUID] = None
    created_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


# ── Savings Goal Schemas ──────────────────────────────────────────────

class SavingsGoalBase(BaseModel):
    name: str = Field(..., description="Goal name (e.g., Fondo de emergencia, Viaje)")
    target_amount: Decimal = Field(..., gt=Decimal("0.00"))
    current_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    deadline: Optional[dt_date] = None
    is_completed: bool = Field(default=False)


class SavingsGoalCreate(SavingsGoalBase):
    user_id: uuid.UUID


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    deadline: Optional[dt_date] = None
    is_completed: Optional[bool] = None


class SavingsGoalRead(SavingsGoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt_datetime

    model_config = ConfigDict(from_attributes=True)


# ── Document & PDF Extraction Schemas ─────────────────────────────────

class ExtractedTransaction(BaseModel):
    date: dt_date
    description: str
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    transaction_type: str = Field(..., description="'expense' or 'income'")
    suggested_category: str = Field(default="Otros")
    reference: Optional[str] = None


class BankStatementPreview(BaseModel):
    filename: str
    period_start: Optional[dt_date] = None
    period_end: Optional[dt_date] = None
    initial_balance: Optional[Decimal] = None
    final_balance: Optional[Decimal] = None
    calculated_balance: Optional[Decimal] = None
    is_balanced: bool = Field(
        ..., description="True if initial_balance + sum(incomes) - sum(expenses) == final_balance"
    )
    transactions: List[ExtractedTransaction] = Field(default_factory=list)


# ── Financial Summaries (Deterministic Output Models) ─────────────────

class CategorySummary(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal = Field(..., description="Percentage of total expense (0-100)")


class FinancialPeriodSummary(BaseModel):
    start_date: dt_date
    end_date: dt_date
    total_income: Decimal
    total_expense: Decimal
    net_savings: Decimal
    savings_rate_percentage: Decimal
    categories_breakdown: List[CategorySummary] = Field(default_factory=list)


class NetWorthSummary(BaseModel):
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    currency: str = "COP"
    accounts: List[AccountRead] = Field(default_factory=list)
    liabilities: List[LiabilityRead] = Field(default_factory=list)

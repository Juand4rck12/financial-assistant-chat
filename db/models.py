import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, utc_now


# ── Enums ─────────────────────────────────────────────────────────────

class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CASH = "cash"
    INVESTMENT = "investment"


class LiabilityType(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    MORTGAGE = "mortgage"


class CategoryType(str, enum.Enum):
    EXPENSE = "expense"
    INCOME = "income"


class ExpenseType(str, enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class IncomeType(str, enum.Enum):
    ACTUAL = "actual"
    PROJECTED = "projected"


class StatementStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    IMPORTED = "imported"
    REJECTED = "rejected"


# ── Models ────────────────────────────────────────────────────────────

class User(Base):
    """User entity representing an individual owner of financial data.
    
    Can authenticate via WhatsApp phone number or Web credentials.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relaciones del usuario
    accounts: Mapped[List["Account"]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    liabilities: Mapped[List["Liability"]] = relationship(
        "Liability", back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="user", cascade="all, delete-orphan"
    )
    incomes: Mapped[List["Income"]] = relationship(
        "Income", back_populates="user", cascade="all, delete-orphan"
    )
    savings_goals: Mapped[List["SavingsGoal"]] = relationship(
        "SavingsGoal", back_populates="user", cascade="all, delete-orphan"
    )
    bank_statements: Mapped[List["BankStatement"]] = relationship(
        "BankStatement", back_populates="user", cascade="all, delete-orphan"
    )


class Account(Base):
    """Financial account representing an asset (bank account, cash, investment)."""
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum"), default=AccountType.SAVINGS, nullable=False
    )
    # Precisión estricta de 14 dígitos con 2 decimales para evitar problemas de coma flotante
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="accounts")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="account")
    incomes: Mapped[List["Income"]] = relationship("Income", back_populates="account")
    bank_statements: Mapped[List["BankStatement"]] = relationship("BankStatement", back_populates="account")

    __table_args__ = (
        Index("ix_accounts_user_active", "user_id", "is_active"),
    )


class Liability(Base):
    """Liability or debt owed by the user (credit card, personal loan, mortgage)."""
    __tablename__ = "liabilities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    liability_type: Mapped[LiabilityType] = mapped_column(
        Enum(LiabilityType, name="liability_type_enum"), default=LiabilityType.CREDIT_CARD, nullable=False
    )
    # Saldo adeudado actual
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), default=Decimal("0.00"), nullable=False
    )
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="liabilities")


class Category(Base):
    """Classification tag for expenses or incomes."""
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type_enum"), default=CategoryType.EXPENSE, nullable=False
    )
    icon: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="categories")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="category_rel")
    incomes: Mapped[List["Income"]] = relationship("Income", back_populates="category_rel")


class Expense(Base):
    """Individual expense record registered by user or extracted from statements."""
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expense_type: Mapped[ExpenseType] = mapped_column(
        Enum(ExpenseType, name="expense_type_enum"), default=ExpenseType.VARIABLE, nullable=False
    )
    statement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("bank_statements.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="expenses")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="expenses")
    category_rel: Mapped[Optional["Category"]] = relationship("Category", back_populates="expenses")
    statement: Mapped[Optional["BankStatement"]] = relationship("BankStatement", back_populates="expenses")

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_expense_amount_positive"),
        Index("ix_expenses_user_date", "user_id", "date"),
    )


class Income(Base):
    """Individual income record (actual or projected)."""
    __tablename__ = "incomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    income_type: Mapped[IncomeType] = mapped_column(
        Enum(IncomeType, name="income_type_enum"), default=IncomeType.ACTUAL, nullable=False
    )
    statement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("bank_statements.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="incomes")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="incomes")
    category_rel: Mapped[Optional["Category"]] = relationship("Category", back_populates="incomes")
    statement: Mapped[Optional["BankStatement"]] = relationship("BankStatement", back_populates="incomes")

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_income_amount_positive"),
        Index("ix_incomes_user_date", "user_id", "date"),
    )


class SavingsGoal(Base):
    """User savings target and progress."""
    __tablename__ = "savings_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False
    )
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=14, scale=2), default=Decimal("0.00"), nullable=False
    )
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="savings_goals")

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="chk_goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="chk_goal_current_non_negative"),
    )


class BankStatement(Base):
    """Record of an uploaded bank statement PDF and audit of its reconciliation."""
    __tablename__ = "bank_statements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    initial_balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    final_balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    calculated_balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus, name="statement_status_enum"), default=StatementStatus.PENDING, nullable=False
    )
    # Almacena transacciones extraídas en staging antes de la confirmación final
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="bank_statements")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="bank_statements")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="statement")
    incomes: Mapped[List["Income"]] = relationship("Income", back_populates="statement")

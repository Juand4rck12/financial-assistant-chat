"""Initial financial schema: users, accounts, liabilities, categories, expenses, incomes, savings_goals, bank_statements.

Revision ID: 0001_initial_financial_schema
Revises: 
Create Date: 2026-09-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_financial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_currency", sa.String(length=3), server_default="COP", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── 2. Accounts (Assets) ────────────────────────────────────────────
    account_type_enum = sa.Enum("checking", "savings", "cash", "investment", name="account_type_enum")
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_type", account_type_enum, nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="COP", nullable=False),
        sa.Column("institution", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_user_active", "accounts", ["user_id", "is_active"])

    # ── 3. Liabilities (Debts) ──────────────────────────────────────────
    liability_type_enum = sa.Enum("credit_card", "personal_loan", "mortgage", name="liability_type_enum")
    op.create_table(
        "liabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("liability_type", liability_type_enum, nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_liabilities_user_id", "liabilities", ["user_id"])

    # ── 4. Categories ───────────────────────────────────────────────────
    category_type_enum = sa.Enum("expense", "income", name="category_type_enum")
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("category_type", category_type_enum, nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])

    # ── 5. Bank Statements ──────────────────────────────────────────────
    statement_status_enum = sa.Enum("pending", "validated", "imported", "rejected", name="statement_status_enum")
    op.create_table(
        "bank_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("initial_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("final_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("calculated_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", statement_status_enum, nullable=False),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bank_statements_user_id", "bank_statements", ["user_id"])

    # ── 6. Expenses ─────────────────────────────────────────────────────
    expense_type_enum = sa.Enum("fixed", "variable", name="expense_type_enum")
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("expense_type", expense_type_enum, nullable=False),
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_statements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="chk_expense_amount_positive"),
    )
    op.create_index("ix_expenses_user_date", "expenses", ["user_id", "date"])

    # ── 7. Incomes ──────────────────────────────────────────────────────
    income_type_enum = sa.Enum("actual", "projected", name="income_type_enum")
    op.create_table(
        "incomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("income_type", income_type_enum, nullable=False),
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_statements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="chk_income_amount_positive"),
    )
    op.create_index("ix_incomes_user_date", "incomes", ["user_id", "date"])

    # ── 8. Savings Goals ────────────────────────────────────────────────
    op.create_table(
        "savings_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_amount > 0", name="chk_goal_target_positive"),
        sa.CheckConstraint("current_amount >= 0", name="chk_goal_current_non_negative"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])


def downgrade() -> None:
    op.drop_table("savings_goals")
    op.drop_table("incomes")
    op.drop_table("expenses")
    op.drop_table("bank_statements")
    op.drop_table("categories")
    op.drop_table("liabilities")
    op.drop_table("accounts")
    op.drop_table("users")

    # Drop enums
    sa.Enum(name="income_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="expense_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="statement_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="category_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="liability_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="account_type_enum").drop(op.get_bind(), checkfirst=True)

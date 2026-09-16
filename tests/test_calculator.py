from decimal import Decimal
import pytest
from core.tools.calculator_tool import (
    calculate_net_worth,
    calculate_percentage,
    calculate_period_balance,
    calculate_savings_rate,
    format_currency_cop,
    to_decimal,
    validate_statement_balance,
)
from core.tools.date_utils import get_period_date_range, parse_user_date
from datetime import date


def test_to_decimal_precision():
    """Verify conversion without floating-point artifacts."""
    assert to_decimal(0.1 + 0.2) == Decimal("0.30")
    assert to_decimal("45000.555") == Decimal("45000.56")
    assert to_decimal(100) == Decimal("100.00")


def test_calculate_net_worth():
    """Verify Net Worth = Assets - Liabilities."""
    assets = [Decimal("1000000.00"), Decimal("500000.00"), Decimal("250000.00")]
    liabilities = [Decimal("350000.00"), Decimal("100000.00")]
    total_assets, total_liab, net_worth = calculate_net_worth(assets, liabilities)

    assert total_assets == Decimal("1750000.00")
    assert total_liab == Decimal("450000.00")
    assert net_worth == Decimal("1300000.00")


def test_calculate_period_balance_and_savings_rate():
    """Verify period balance and savings rate calculations."""
    incomes = Decimal("5000000.00")
    expenses = Decimal("3500000.00")

    balance = calculate_period_balance(incomes, expenses)
    assert balance == Decimal("1500000.00")

    rate = calculate_savings_rate(incomes, expenses)
    # (1.500.000 / 5.000.000) * 100 = 30.00%
    assert rate == Decimal("30.00")

    # Caso con 0 ingresos
    assert calculate_savings_rate(Decimal("0.00"), expenses) == Decimal("0.00")


def test_calculate_percentage():
    assert calculate_percentage(25, 100) == Decimal("25.00")
    assert calculate_percentage(0, 100) == Decimal("0.00")
    assert calculate_percentage(50, 0) == Decimal("0.00")


def test_validate_statement_balance():
    """Verify statement mathematical checksum."""
    initial = Decimal("100000.00")
    incomes = Decimal("250000.00")
    expenses = Decimal("50000.00")
    # Saldo correcto = 100000 + 250000 - 50000 = 300000
    final = Decimal("300000.00")

    balanced, calculated, diff = validate_statement_balance(initial, final, incomes, expenses)
    assert balanced is True
    assert calculated == Decimal("300000.00")
    assert diff == Decimal("0.00")

    # Caso descuadrado
    bad_final = Decimal("280000.00")
    balanced, calculated, diff = validate_statement_balance(initial, bad_final, incomes, expenses)
    assert balanced is False
    assert diff == Decimal("20000.00")


def test_format_currency_cop():
    """Verify COP currency formatting without markdown."""
    assert format_currency_cop(25000) == "$ 25.000 COP"
    assert format_currency_cop(1500000) == "$ 1.500.000 COP"
    assert format_currency_cop(-45000) == "-$ 45.000 COP"


def test_date_utils():
    """Verify deterministic conversion of periods."""
    ref = date(2026, 9, 16)  # Miércoles
    start, end, label = get_period_date_range("hoy", reference_date=ref)
    assert start == ref
    assert end == ref
    assert label == "Hoy"

    start, end, label = get_period_date_range("ayer", reference_date=ref)
    assert start == date(2026, 9, 15)
    assert end == date(2026, 9, 15)

    start, end, label = get_period_date_range("este mes", reference_date=ref)
    assert start == date(2026, 9, 1)
    assert end == date(2026, 9, 30)

    parsed = parse_user_date("2026-09-10")
    assert parsed == date(2026, 9, 10)

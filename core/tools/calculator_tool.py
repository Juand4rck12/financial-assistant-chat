from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Tuple


def to_decimal(val: int | float | str | Decimal) -> Decimal:
    """Safely convert any numeric input into a 2-decimal place Decimal.
    
    Prevents floating-point representation artifacts.
    """
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Convertir floats a str primero para evitar representación binaria espuria
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_net_worth(
    asset_balances: Iterable[Decimal | float | int | str],
    liability_balances: Iterable[Decimal | float | int | str],
) -> Tuple[Decimal, Decimal, Decimal]:
    """Calculate total assets, total liabilities, and net worth deterministically.
    
    Fórmula: Patrimonio Neto = Total Activos - Total Pasivos.
    Retorna: (total_assets, total_liabilities, net_worth)
    """
    total_assets = sum((to_decimal(b) for b in asset_balances), start=Decimal("0.00"))
    total_liabilities = sum((to_decimal(b) for b in liability_balances), start=Decimal("0.00"))
    net_worth = total_assets - total_liabilities
    return (
        total_assets.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_liabilities.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        net_worth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )


def calculate_period_balance(
    total_incomes: Decimal | float | int | str,
    total_expenses: Decimal | float | int | str,
) -> Decimal:
    """Calculate net savings for a period: Incomes - Expenses.
    
    Cálculo puro: Ahorro Neto = Ingresos - Gastos.
    """
    inc = to_decimal(total_incomes)
    exp = to_decimal(total_expenses)
    return (inc - exp).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_savings_rate(
    total_incomes: Decimal | float | int | str,
    total_expenses: Decimal | float | int | str,
) -> Decimal:
    """Calculate savings rate percentage: (Net Savings / Incomes) * 100.
    
    Si el ingreso es 0 o negativo, retorna 0.00%.
    """
    inc = to_decimal(total_incomes)
    exp = to_decimal(total_expenses)
    if inc <= Decimal("0.00"):
        return Decimal("0.00")
    net_savings = inc - exp
    rate = (net_savings / inc) * Decimal("100.00")
    return rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_percentage(
    part: Decimal | float | int | str,
    total: Decimal | float | int | str,
) -> Decimal:
    """Calculate percentage share: (part / total) * 100."""
    p = to_decimal(part)
    t = to_decimal(total)
    if t <= Decimal("0.00"):
        return Decimal("0.00")
    pct = (p / t) * Decimal("100.00")
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_statement_balance(
    initial_balance: Decimal | float | int | str,
    final_balance: Decimal | float | int | str,
    total_incomes: Decimal | float | int | str,
    total_expenses: Decimal | float | int | str,
    tolerance: Decimal = Decimal("0.05"),
) -> Tuple[bool, Decimal, Decimal]:
    """Validate bank statement control sum.
    
    Regla bancaria estricta:
    Saldo Calculado = Saldo Inicial + Total Abonos - Total Cargos
    Diferencia = Saldo Final - Saldo Calculado
    
    Retorna: (is_balanced, calculated_balance, difference)
    """
    ini = to_decimal(initial_balance)
    fin = to_decimal(final_balance)
    inc = to_decimal(total_incomes)
    exp = to_decimal(total_expenses)

    calculated = (ini + inc - exp).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    diff = abs(fin - calculated).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    is_balanced = diff <= tolerance
    return is_balanced, calculated, diff


def format_currency_cop(amount: Decimal | float | int | str) -> str:
    """Format an amount into Colombian Peso standard format without markdown.
    
    Ejemplo:
    - 25000 -> "$ 25.000 COP"
    - 1500350.50 -> "$ 1.500.351 COP" (redondeo estándar para COP)
    - -50000 -> "-$ 50.000 COP"
    """
    d = to_decimal(amount)
    is_negative = d < Decimal("0.00")
    abs_d = abs(d)

    # Redondeamos a entero en COP ya que centavos casi no se usan en moneda física/comercial
    rounded_int = int(abs_d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    formatted_int = f"{rounded_int:,}".replace(",", ".")

    prefix = "-$ " if is_negative else "$ "
    return f"{prefix}{formatted_int} COP"

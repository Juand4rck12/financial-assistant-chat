import calendar
from datetime import date, datetime, timedelta
from typing import Optional, Tuple


MONTH_NAMES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def parse_user_date(raw_date_str: str, reference_date: Optional[date] = None) -> date:
    """Parse a flexible date string into a concrete Python date.
    
    Handles:
    - 'hoy', 'ayer'
    - 'YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY'
    """
    ref = reference_date or date.today()
    clean = raw_date_str.strip().lower()

    if clean in ("hoy", "today"):
        return ref
    if clean in ("ayer", "yesterday"):
        return ref - timedelta(days=1)

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue

    # Fallback to reference date if unparseable
    return ref


def get_period_date_range(
    period_expression: str, reference_date: Optional[date] = None
) -> Tuple[date, date, str]:
    """Deterministically convert a natural language period into [start_date, end_date].
    
    Returns: (start_date, end_date, label)
    
    Previene cualquier cálculo o confusión temporal por parte del LLM.
    """
    ref = reference_date or date.today()
    expr = period_expression.strip().lower()

    if "hoy" in expr:
        return ref, ref, "Hoy"

    if "ayer" in expr:
        yesterday = ref - timedelta(days=1)
        return yesterday, yesterday, "Ayer"

    if "esta semana" in expr or "semana actual" in expr:
        # Lunes de esta semana
        start_of_week = ref - timedelta(days=ref.weekday())
        # Domingo de esta semana
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week, "Esta semana"

    if "semana pasada" in expr or "semana anterior" in expr:
        start_of_last_week = ref - timedelta(days=ref.weekday() + 7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        return start_of_last_week, end_of_last_week, "Semana pasada"

    if "mes pasado" in expr or "mes anterior" in expr:
        # Primer día del mes anterior
        first_of_this_month = ref.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        start_date = last_of_prev_month.replace(day=1)
        return start_date, last_of_prev_month, "Mes pasado"

    # Revisar si se menciona un mes específico (ej: 'en agosto', 'julio')
    for month_name, month_num in MONTH_NAMES_ES.items():
        if month_name in expr:
            year = ref.year
            # Si el mes mencionado es futuro respecto a hoy, probablemente sea del año anterior
            if month_num > ref.month and "este año" not in expr:
                year = ref.year - 1
            last_day = calendar.monthrange(year, month_num)[1]
            return date(year, month_num, 1), date(year, month_num, last_day), month_name.capitalize()

    if "este año" in expr or "año actual" in expr:
        return date(ref.year, 1, 1), date(ref.year, 12, 31), f"Año {ref.year}"

    if "año pasado" in expr or "año anterior" in expr:
        prev_year = ref.year - 1
        return date(prev_year, 1, 1), date(prev_year, 12, 31), f"Año {prev_year}"

    # Por defecto: Mes actual (desde el día 1 hasta el último día del mes)
    last_day = calendar.monthrange(ref.year, ref.month)[1]
    return date(ref.year, ref.month, 1), date(ref.year, ref.month, last_day), "Este mes"

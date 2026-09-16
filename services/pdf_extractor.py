import io
import logging
import re
from datetime import date
from decimal import Decimal
from typing import BinaryIO, List, Optional, Tuple

import pdfplumber

from core.models.schemas import BankStatementPreview, ExtractedTransaction
from core.tools.calculator_tool import to_decimal, validate_statement_balance
from core.tools.date_utils import parse_user_date

logger = logging.getLogger(__name__)


class BankStatementExtractor:
    """Extracts, categorizes and mathematically verifies bank statement PDFs."""

    def extract_from_stream(
        self, file_stream: BinaryIO, filename: str = "statement.pdf"
    ) -> BankStatementPreview:
        """Extract transactions and balances from a PDF byte stream."""
        raw_text = ""
        extracted_txs: List[ExtractedTransaction] = []
        initial_balance = Decimal("0.00")
        final_balance = Decimal("0.00")
        period_start: Optional[date] = None
        period_end: Optional[date] = None

        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                raw_text += text + "\n"

                # 1. Extracción de tablas tabulares nativas si existen
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        tx = self._parse_table_row(row)
                        if tx:
                            extracted_txs.append(tx)

        # 2. Si no se extrajeron mediante tablas tabulares, intentar extracción por regex de líneas
        if not extracted_txs:
            extracted_txs = self._extract_transactions_from_text(raw_text)

        # 3. Extraer balances de encabezados / pie de página
        init_bal, fin_bal, p_start, p_end = self._extract_statement_metadata(raw_text)
        if init_bal is not None:
            initial_balance = init_bal
        if fin_bal is not None:
            final_balance = fin_bal
        if p_start:
            period_start = p_start
        if p_end:
            period_end = p_end

        # 4. Suma de control matemática estricta (Cero Alucinaciones)
        total_incomes = sum(
            (tx.amount for tx in extracted_txs if tx.transaction_type == "income"),
            start=Decimal("0.00"),
        )
        total_expenses = sum(
            (tx.amount for tx in extracted_txs if tx.transaction_type == "expense"),
            start=Decimal("0.00"),
        )

        is_balanced, calculated, diff = validate_statement_balance(
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_incomes=total_incomes,
            total_expenses=total_expenses,
        )

        return BankStatementPreview(
            filename=filename,
            period_start=period_start,
            period_end=period_end,
            initial_balance=initial_balance,
            final_balance=final_balance,
            calculated_balance=calculated,
            is_balanced=is_balanced,
            transactions=extracted_txs,
        )

    def _parse_table_row(self, row: List[Optional[str]]) -> Optional[ExtractedTransaction]:
        """Attempt to parse a tabular row [Date, Description, Amount, ...]."""
        if not row or len(row) < 3:
            return None

        # Limpiar celdas
        clean_row = [cell.strip() if cell else "" for cell in row]
        first_cell = clean_row[0]

        # Verificar si la primera columna parece una fecha (DD/MM/YYYY o YYYY-MM-DD o DD-MM)
        date_match = re.search(r"\b(\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|\d{1,2}[/-]\d{1,2})\b", first_cell)
        if not date_match:
            return None

        tx_date = parse_user_date(date_match.group(1))
        description = clean_row[1] if len(clean_row) > 1 else "Transacción"

        # Buscar celda con valor monetario
        amount: Optional[Decimal] = None
        tx_type = "expense"

        for cell in clean_row[2:]:
            amt_match = re.search(r"[-+]?\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\d+)", cell)
            if amt_match:
                norm = amt_match.group(1).replace(".", "").replace(",", ".")
                try:
                    parsed_val = Decimal(norm)
                    if parsed_val > Decimal("0"):
                        amount = parsed_val
                        # Si tiene signo positivo o palabra 'abono'/'ingreso'
                        if "+" in cell or "abono" in cell.lower() or "credito" in cell.lower():
                            tx_type = "income"
                        break
                except Exception:
                    continue

        if not amount:
            return None

        suggested_cat = self._categorize_description(description)

        return ExtractedTransaction(
            date=tx_date,
            description=description,
            amount=amount,
            transaction_type=tx_type,
            suggested_category=suggested_cat,
        )

    def _extract_transactions_from_text(self, text: str) -> List[ExtractedTransaction]:
        """Fallback line-by-line regex parser for bank statements."""
        txs: List[ExtractedTransaction] = []
        lines = text.split("\n")

        # Patrón típico: Fecha | Descripción | Monto al final de la línea
        line_pattern = re.compile(
            r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+(.+?)\s+([-+]?\$?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*$"
        )

        for line in lines:
            match = line_pattern.search(line)
            if match:
                raw_date = match.group(1)
                desc = match.group(2).strip()
                raw_amount = match.group(3).strip()

                if len(desc) < 3 or any(w in desc.lower() for w in ["saldo", "balance", "total", "página"]):
                    continue

                tx_date = parse_user_date(raw_date)
                norm_amt = raw_amount.replace("$", "").replace(".", "").replace(",", ".").replace("+", "").strip()
                try:
                    val = Decimal(norm_amt)
                    tx_type = "income" if "+" in raw_amount or "abono" in desc.lower() or "nómina" in desc.lower() else "expense"
                    cat = self._categorize_description(desc)

                    txs.append(
                        ExtractedTransaction(
                            date=tx_date,
                            description=desc,
                            amount=val,
                            transaction_type=tx_type,
                            suggested_category=cat,
                        )
                    )
                except Exception:
                    continue

        return txs

    def _extract_statement_metadata(
        self, text: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[date], Optional[date]]:
        """Extract initial/final balance and statement period dates."""
        initial_balance: Optional[Decimal] = None
        final_balance: Optional[Decimal] = None
        start_date: Optional[date] = None
        end_date: Optional[date] = None

        # Saldo inicial
        init_match = re.search(
            r"saldo\s+(?:anterior|inicial)[^\d\n]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
            text,
            re.IGNORECASE,
        )
        if init_match:
            initial_balance = to_decimal(init_match.group(1).replace(".", "").replace(",", "."))

        # Saldo final
        fin_match = re.search(
            r"saldo\s+(?:actual|final|nuevo)[^\d\n]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
            text,
            re.IGNORECASE,
        )
        if fin_match:
            final_balance = to_decimal(fin_match.group(1).replace(".", "").replace(",", "."))

        return initial_balance, final_balance, start_date, end_date

    def _categorize_description(self, desc: str) -> str:
        """Infer financial category from transaction text."""
        d = desc.lower()
        if any(w in d for w in ["exito", "carulla", "jumbo", "d1", "ara", "olimpica", "restaurante", "ubereats", "rappi"]):
            return "Alimentación"
        if any(w in d for w in ["uber", "didi", "terpel", "texaco", "primax", "peaje"]):
            return "Transporte"
        if any(w in d for w in ["enel", "epm", "etb", "claro", "tigo", "movistar", "acueducto"]):
            return "Servicios"
        if any(w in d for w in ["netflix", "spotify", "cine", "playstation", "steam"]):
            return "Ocio"
        if any(w in d for w in ["cruz verde", "drogueria", "farmatodo", "salud"]):
            return "Salud"
        if any(w in d for w in ["nomina", "salario", "transferencia recibida", "abono"]):
            return "Ingresos"
        return "Varios"


pdf_extractor = BankStatementExtractor()

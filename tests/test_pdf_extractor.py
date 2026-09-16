import io
from datetime import date
from decimal import Decimal
import pytest
from pypdf import PdfWriter
from fastapi.testclient import TestClient

from main import app
from db.models import AccountType
from core.tools.db_tool import create_account, get_or_create_user
import db.connection as db_conn
from services.pdf_extractor import pdf_extractor


def create_dummy_pdf_with_text(text: str) -> bytes:
    """Create a minimal valid PDF in memory containing test statement text."""
    # Usando pypdf para crear un stream PDF simple
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def test_table_row_parsing():
    """Verify table row parsing into ExtractedTransaction."""
    row = ["15/09/2026", "Supermercado Exito 123", "$ 145.200"]
    tx = pdf_extractor._parse_table_row(row)

    assert tx is not None
    assert tx.date == date(2026, 9, 15)
    assert tx.description == "Supermercado Exito 123"
    assert tx.amount == Decimal("145200.00")
    assert tx.transaction_type == "expense"
    assert tx.suggested_category == "Alimentación"


def test_table_row_income_parsing():
    """Verify positive / credit table row parsing."""
    row = ["16/09/2026", "Abono Nomina Empresa SAS", "+$ 2.500.000"]
    tx = pdf_extractor._parse_table_row(row)

    assert tx is not None
    assert tx.date == date(2026, 9, 16)
    assert tx.amount == Decimal("2500000.00")
    assert tx.transaction_type == "income"
    assert tx.suggested_category == "Ingresos"


def test_text_regex_extraction():
    """Verify fallback text extraction on raw bank statement dump."""
    raw_statement_text = """
    EXTRACTO BANCARIO BANCOLOMBIA
    Saldo Anterior: $ 1.000.000
    
    10/09/2026 Restaurante La 93   $ 45.000
    12/09/2026 Estacion Texaco     $ 80.000
    15/09/2026 Abono Salario       +$ 2.000.000
    
    Saldo Final: $ 2.875.000
    """
    txs = pdf_extractor._extract_transactions_from_text(raw_statement_text)
    assert len(txs) == 3

    init_bal, fin_bal, _, _ = pdf_extractor._extract_statement_metadata(raw_statement_text)
    assert init_bal == Decimal("1000000.00")
    assert fin_bal == Decimal("2875000.00")

    # Validación matemática: 1.000.000 + 2.000.000 - 45.000 - 80.000 = 2.875.000
    incomes = sum(t.amount for t in txs if t.transaction_type == "income")
    expenses = sum(t.amount for t in txs if t.transaction_type == "expense")
    assert incomes == Decimal("2000000.00")
    assert expenses == Decimal("125000.00")
    assert (init_bal + incomes - expenses) == fin_bal


@pytest.mark.asyncio
async def test_upload_statement_api_endpoint():
    """Verify document upload endpoint with a valid PDF."""
    await db_conn.init_db()
    session_factory = db_conn.get_session_factory()
    async with session_factory() as session:
        user = await get_or_create_user(session, "+573008889900", "Valeria")
        account = await create_account(
            session, user.id, "Bancolombia", AccountType.SAVINGS, Decimal("1000000.00")
        )
        user_id = str(user.id)
        account_id = str(account.id)

    dummy_pdf = create_dummy_pdf_with_text("Extracto Bancario")
    client = TestClient(app)

    response = client.post(
        f"/api/v1/documents/upload-statement?user_id={user_id}&account_id={account_id}",
        files={"file": ("extracto_septiembre.pdf", dummy_pdf, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "extracto_septiembre.pdf"
    assert "is_balanced" in data

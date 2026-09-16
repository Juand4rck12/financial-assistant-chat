import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.schemas import BankStatementPreview
from core.tools.db_tool import create_expense, create_income
from db.connection import get_db_session
from db.models import BankStatement, StatementStatus
from services.pdf_extractor import pdf_extractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload-statement", response_model=BankStatementPreview)
async def upload_bank_statement(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    account_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Upload a bank statement PDF, extract transactions and verify control balance.
    
    Stores the extracted transactions in staging status (PENDING) for user confirmation.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        preview = pdf_extractor.extract_from_stream(io.BytesIO(file_bytes), filename=file.filename)
    except Exception as err:
        logger.error("Error extracting PDF statement: %s", err, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract bank statement: {str(err)}")

    # Guardar en base de datos en estado PENDING con metadata de auditoría
    statement = BankStatement(
        id=uuid.uuid4(),
        user_id=user_id,
        account_id=account_id,
        filename=file.filename,
        period_start=preview.period_start,
        period_end=preview.period_end,
        initial_balance=preview.initial_balance,
        final_balance=preview.final_balance,
        calculated_balance=preview.calculated_balance,
        status=StatementStatus.VALIDATED if preview.is_balanced else StatementStatus.PENDING,
        raw_metadata={
            "is_balanced": preview.is_balanced,
            "transactions": [
                {
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": str(tx.amount),
                    "transaction_type": tx.transaction_type,
                    "suggested_category": tx.suggested_category,
                    "reference": tx.reference,
                }
                for tx in preview.transactions
            ],
        },
    )
    session.add(statement)
    await session.commit()

    return preview


@router.post("/confirm-statement/{statement_id}")
async def confirm_bank_statement(
    statement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Commit validated transactions from a staged bank statement into financial records."""
    stmt = select(BankStatement).where(BankStatement.id == statement_id)
    res = await session.execute(stmt)
    statement = res.scalar_one_or_none()

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found.")

    if statement.status == StatementStatus.IMPORTED:
        raise HTTPException(status_code=400, detail="Statement has already been imported.")

    raw_data = statement.raw_metadata or {}
    txs_data = raw_data.get("transactions", [])

    imported_expenses = 0
    imported_incomes = 0

    for tx in txs_data:
        from core.tools.date_utils import parse_user_date
        tx_date = parse_user_date(tx["date"])
        amt = tx["amount"]

        if tx["transaction_type"] == "expense":
            await create_expense(
                session=session,
                user_id=statement.user_id,
                amount=amt,
                category=tx.get("suggested_category", "Varios"),
                description=tx["description"],
                transaction_date=tx_date,
                account_id=statement.account_id,
                statement_id=statement.id,
            )
            imported_expenses += 1
        else:
            await create_income(
                session=session,
                user_id=statement.user_id,
                amount=amt,
                source=tx["description"],
                description=tx.get("reference"),
                transaction_date=tx_date,
                account_id=statement.account_id,
                statement_id=statement.id,
            )
            imported_incomes += 1

    statement.status = StatementStatus.IMPORTED
    await session.commit()

    return {
        "status": "success",
        "statement_id": str(statement.id),
        "imported_expenses": imported_expenses,
        "imported_incomes": imported_incomes,
        "total_imported": imported_expenses + imported_incomes,
    }

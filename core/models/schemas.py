from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    expense = "expense"
    income = "income"
    transfer = "transfer"


class CategoryType(str, Enum):
    expense = "expense"
    income = "income"


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: Decimal = Field(gt=0, decimal_places=2)
    category: str
    description: Optional[str] = None
    date: datetime = Field(default_factory=datetime.now)
    user_id: str


class TransactionResponse(BaseModel):
    id: int
    type: TransactionType
    amount: Decimal
    category: str
    description: Optional[str]
    date: datetime
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryBase(BaseModel):
    name: str
    type: CategoryType
    icon: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int

    model_config = {"from_attributes": True}


class FinancialGoal(BaseModel):
    id: Optional[int] = None
    user_id: str
    name: str
    target_amount: Decimal = Field(gt=0, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    deadline: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ReportRequest(BaseModel):
    user_id: str
    period: str = "monthly"
    year: int
    month: Optional[int] = None


class WhatsAppMessage(BaseModel):
    from_number: str
    text: Optional[str] = None
    audio_url: Optional[str] = None
    message_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentResponse(BaseModel):
    message: str
    data: Optional[dict] = None

"""schemas/portfolio.py — Portfolio and Holding schemas for PMRI India."""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class HoldingInput(BaseModel):
    symbol: str
    exchange: str = "NSE"
    quantity: float

class HoldingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    exchange: str
    quantity: float

class PortfolioCreate(BaseModel):
    name: str = "My Portfolio"
    org_id: Optional[str] = None

class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    user_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    created_at: datetime
    status: str = "ACTIVE"
    holdings: List[HoldingResponse] = []
    portfolio_value_inr: Optional[float] = None

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None

class CsvUploadResult(BaseModel):
    accepted: List[HoldingInput] = []
    rejected: List[dict] = []   # [{"row": ..., "reason": ...}]
    message: str

class PortfolioValueResponse(BaseModel):
    portfolio_id: str
    total_value_inr: float
    holdings: List[dict]   # includes current_price, value_inr, weight

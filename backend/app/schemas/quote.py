"""schemas/quote.py — Quote schemas for PMRI India."""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class QuoteRequest(BaseModel):
    portfolio_id: str
    term: str                     # INTRADAY | WEEKLY | MONTHLY
    notional_inr: float
    org_id: Optional[str] = None  # if quoting under an org context

class MLInferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_version: str
    tail_loss_prob: float
    predicted_vol: float
    portfolio_signals: dict

class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    term: str
    notional_inr: float
    premium_inr: float
    loss_threshold: float
    profit_threshold: float
    coverage_rate: float
    profit_share_rate: float
    max_payout_inr: float
    expected_payout: float
    risk_margin: float
    capital_fee: float
    eligible: bool
    eligibility_reasons: List[str]
    rules_version: str
    status: str
    created_at: datetime
    portfolio_value_inr: float
    portfolio_snapshot: dict
    ml_inference: Optional[MLInferenceResponse] = None

class PolicyBindRequest(BaseModel):
    quote_id: str

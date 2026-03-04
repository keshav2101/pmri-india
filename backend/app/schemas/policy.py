"""schemas/policy.py — Policy, Settlement, Ledger, and Rules schemas for PMRI India."""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    end_portfolio_value: float
    portfolio_return_pct: float
    payout_inr: float
    surplus_inr: float
    outcome: str
    settled_at: datetime

class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    term: str
    notional_inr: float
    premium_inr: float
    loss_threshold: float
    profit_threshold: float
    coverage_rate: float
    profit_share_rate: float
    max_payout_inr: float
    start_portfolio_value: float
    portfolio_snapshot: dict
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime
    portfolio_id: UUID
    user_id: Optional[UUID] = None
    org_id: Optional[UUID] = None
    settlement: Optional[SettlementResponse] = None

class LedgerTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    tx_type: str
    amount_inr: float
    description: str
    created_at: datetime

class RulesConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tier: str
    config_json: Dict[str, Any]
    updated_at: datetime

class RulesConfigUpdate(BaseModel):
    config_json: Dict[str, Any]

class SettlementRunResponse(BaseModel):
    term: Optional[str]
    policies_checked: int
    policies_settled: int
    errors: int
    details: List[dict]

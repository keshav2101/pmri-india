"""routers/quotes.py — Quotes router integrating portfolio pricing and underwriting."""
from __future__ import annotations
import logging
import uuid
import sys
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org import OrgMember
from app.models.portfolio import Portfolio, Holding
from app.models.quote import Quote, MLInference
from app.models.policy import Policy, RulesConfig
from app.schemas.quote import QuoteRequest, QuoteResponse, MLInferenceResponse
from app.services.market_service import market_service
from app.services.ml_service import ml_service

# Load ML module pricing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
from pricing import DEFAULT_RULES, check_underwriting

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quotes", tags=["Quotes"])

@router.post("", response_model=QuoteResponse, status_code=201)
async def create_quote(req: QuoteRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Fetch portfolio & validate access
    p = (await db.execute(select(Portfolio).where(Portfolio.id == uuid.UUID(req.portfolio_id)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Portfolio not found.")
        
    if req.org_id:
        if str(p.org_id) != req.org_id:
            raise HTTPException(400, "Portfolio does not belong to specified org.")
        m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == uuid.UUID(req.org_id), OrgMember.user_id == current_user.id))
        if not m_q.scalar_one_or_none():
            raise HTTPException(403, "Access denied to org.")
        tier = p.org.tier if p.org else "INSTITUTIONAL_BASIC"
    else:
        if p.user_id != current_user.id:
            raise HTTPException(403, "Access denied.")
        tier = current_user.tier

    # 2. Get holdings & compute portfolio value
    holdings = (await db.execute(select(Holding).where(Holding.portfolio_id == p.id))).scalars().all()
    if not holdings:
        raise HTTPException(400, "Cannot quote an empty portfolio.")

    total_value = 0.0
    snapshot_data = {}
    ml_holdings = []
    
    for h in holdings:
        price = market_service.get_current_price(h.symbol)
        val = price * h.quantity
        total_value += val
        snapshot_data[h.symbol] = {"qty": h.quantity, "price": price}
        
    for h in holdings:
        price = snapshot_data[h.symbol]["price"]
        w = (price * h.quantity) / total_value
        prices = market_service.get_historical_prices(h.symbol, days=252)
        ml_holdings.append({"symbol": h.symbol, "weight": w, "prices": prices})

    # 3. Determine config
    rules_rec = (await db.execute(select(RulesConfig).where(RulesConfig.tier == tier))).scalar_one_or_none()
    rules_dict = {tier: rules_rec.config_json} if rules_rec else DEFAULT_RULES
    rules_version = str(rules_rec.id) if rules_rec else "default-v1"
    
    # 4. Compute current exposure (sum of active/matured policies)
    if req.org_id:
        pol_q = select(Policy.notional_inr).where(Policy.org_id == uuid.UUID(req.org_id), Policy.status.in_(["ACTIVE", "MATURED"]))
    else:
        pol_q = select(Policy.notional_inr).where(Policy.user_id == current_user.id, Policy.org_id.is_(None), Policy.status.in_(["ACTIVE", "MATURED"]))
    
    exposure = sum((await db.execute(pol_q)).scalars().all())
    
    # 5. ML Inference
    import ml.pricing as ml_pricing
    term_days = ml_pricing.TERM_DAYS.get(req.term.upper(), 30)
    pred = ml_service.predict_tail_loss(ml_holdings, term_days)
    
    inference = MLInference(
        model_version=pred["model_version"],
        portfolio_signals=pred["portfolio_features"],
        tail_loss_prob=pred["tail_loss_prob"],
        predicted_vol=pred["predicted_vol"]
    )
    db.add(inference)
    await db.flush()
    
    # 6. Pricing & Underwriting
    import ml.pricing as mlp
    quote_res = mlp.compute_portfolio_quote(
        notional=req.notional_inr,
        term=req.term.upper(),
        tail_loss_prob=pred["tail_loss_prob"],
        predicted_vol=pred["predicted_vol"],
        portfolio_feats=pred["portfolio_features"],
        tier=tier,
        current_exposure=exposure,
        rules=rules_dict
    )
    
    q = Quote(
        user_id=current_user.id,
        org_id=uuid.UUID(req.org_id) if req.org_id else None,
        portfolio_id=p.id,
        ml_inference_id=inference.id,
        term=req.term.upper(),
        portfolio_snapshot=snapshot_data,
        portfolio_value_inr=total_value,
        notional_inr=req.notional_inr,
        premium_inr=quote_res.premium_inr,
        loss_threshold=quote_res.loss_threshold,
        profit_threshold=quote_res.profit_threshold,
        coverage_rate=quote_res.coverage_rate,
        profit_share_rate=quote_res.profit_share_rate,
        max_payout_inr=quote_res.max_payout_inr,
        expected_payout=quote_res.expected_payout,
        risk_margin=quote_res.risk_margin,
        capital_fee=quote_res.capital_fee,
        eligible=quote_res.eligibility.eligible,
        eligibility_reasons=quote_res.eligibility.reasons,
        rules_version=rules_version,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    
    return QuoteResponse.model_validate(q)


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    q = (await db.execute(select(Quote).options(selectinload(Quote.ml_inference)).where(Quote.id == uuid.UUID(quote_id)))).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Quote not found.")
    
    if q.org_id:
        m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == q.org_id, OrgMember.user_id == current_user.id))
        if not m_q.scalar_one_or_none() and not current_user.is_admin:
            raise HTTPException(403, "Access denied.")
    elif q.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
        
    return QuoteResponse.model_validate(q)

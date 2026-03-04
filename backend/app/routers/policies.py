"""routers/policies.py — Policies router for purchasing and viewing bound quotes."""
from __future__ import annotations
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org import OrgMember
from app.models.quote import Quote
from app.models.policy import Policy, LedgerTransaction
from app.schemas.quote import PolicyBindRequest
from app.schemas.policy import PolicyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
async def bind_policy(req: PolicyBindRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Convert an eligible Quote into an active Policy (Purchase)."""
    q_rec = (await db.execute(select(Quote).where(Quote.id == uuid.UUID(req.quote_id)))).scalar_one_or_none()
    if not q_rec:
        raise HTTPException(404, "Quote not found.")
        
    if q_rec.status != "QUOTED":
        raise HTTPException(400, f"Quote is already {q_rec.status}.")
        
    if not q_rec.eligible:
        raise HTTPException(400, f"Cannot purchase ineligible quote. Reasons: {q_rec.eligibility_reasons}")
        
    # Check org access
    if q_rec.org_id:
        m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == q_rec.org_id, OrgMember.user_id == current_user.id))
        if not m_q.scalar_one_or_none() and not current_user.is_admin:
            raise HTTPException(403, "Access denied to org.")
    elif q_rec.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")

    # Determine end date
    now = datetime.now(timezone.utc)
    if q_rec.term == "INTRADAY":
        # For MVP demo, ends essentially immediately (same day). Will be caught by maturity check
        end_date = now.replace(hour=23, minute=59, second=59)
    elif q_rec.term == "WEEKLY":
        end_date = now + timedelta(days=7)
    elif q_rec.term == "MONTHLY":
        end_date = now + timedelta(days=30)
    else:
        end_date = now + timedelta(days=30)
        
    p = Policy(
        quote_id=q_rec.id,
        user_id=current_user.id,
        org_id=q_rec.org_id,
        portfolio_id=q_rec.portfolio_id,
        term=q_rec.term,
        notional_inr=q_rec.notional_inr,
        premium_inr=q_rec.premium_inr,
        loss_threshold=q_rec.loss_threshold,
        profit_threshold=q_rec.profit_threshold,
        coverage_rate=q_rec.coverage_rate,
        profit_share_rate=q_rec.profit_share_rate,
        max_payout_inr=q_rec.max_payout_inr,
        start_portfolio_value=q_rec.portfolio_value_inr,
        portfolio_snapshot=q_rec.portfolio_snapshot,
        start_date=now,
        end_date=end_date,
        status="ACTIVE"
    )
    db.add(p)
    q_rec.status = "CONVERTED"
    await db.flush()
    
    # Write ledger entry for premium
    tx = LedgerTransaction(
        policy_id=p.id,
        tx_type="PREMIUM_PAID",
        amount_inr=q_rec.premium_inr,
        description=f"Premium collected for policy {p.id}"
    )
    db.add(tx)
    
    await db.commit()
    # Re-fetch with settlement eagerly loaded to avoid MissingGreenlet during serialization
    result = await db.execute(
        select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == p.id)
    )
    p = result.scalar_one()
    return PolicyResponse.model_validate(p)


@router.get("", response_model=List[PolicyResponse])
async def list_policies(org_id: str = None, status: str = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = select(Policy).options(selectinload(Policy.settlement))
    
    if org_id:
        if not current_user.is_admin:
            m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == uuid.UUID(org_id), OrgMember.user_id == current_user.id))
            if not m_q.scalar_one_or_none():
                raise HTTPException(403, "Access denied.")
        q = q.where(Policy.org_id == uuid.UUID(org_id))
    else:
        q = q.where(Policy.user_id == current_user.id, Policy.org_id.is_(None))
        
    if status:
        q = q.where(Policy.status == status.upper())
        
    return (await db.execute(q.order_by(Policy.created_at.desc()))).scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = (await db.execute(select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Policy not found.")
        
    if p.org_id:
        m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == p.org_id, OrgMember.user_id == current_user.id))
        if not m_q.scalar_one_or_none() and not current_user.is_admin:
            raise HTTPException(403, "Access denied.")
    elif p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
        
    return PolicyResponse.model_validate(p)


@router.patch("/{policy_id}/deactivate", response_model=PolicyResponse)
async def deactivate_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deactivate an ACTIVE policy (suspends coverage without deleting)."""
    p = (await db.execute(select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Policy not found.")
    if p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
    if p.status != "ACTIVE":
        raise HTTPException(400, f"Only ACTIVE policies can be deactivated. Current status: {p.status}")
    p.status = "INACTIVE"
    db.add(LedgerTransaction(
        policy_id=p.id, tx_type="DEACTIVATION", amount_inr=0,
        description="Policy deactivated by user"
    ))
    await db.commit()
    result = await db.execute(select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == p.id))
    return PolicyResponse.model_validate(result.scalar_one())


@router.patch("/{policy_id}/activate", response_model=PolicyResponse)
async def activate_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Re-activate an INACTIVE policy."""
    p = (await db.execute(select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Policy not found.")
    if p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
    if p.status != "INACTIVE":
        raise HTTPException(400, f"Only INACTIVE policies can be re-activated. Current status: {p.status}")
    p.status = "ACTIVE"
    db.add(LedgerTransaction(
        policy_id=p.id, tx_type="ACTIVATION", amount_inr=0,
        description="Policy re-activated by user"
    ))
    await db.commit()
    result = await db.execute(select(Policy).options(selectinload(Policy.settlement)).where(Policy.id == p.id))
    return PolicyResponse.model_validate(result.scalar_one())


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete an INACTIVE, CANCELLED, or SETTLED policy."""
    p = (await db.execute(select(Policy).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Policy not found.")
    if p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
    if p.status == "ACTIVE":
        raise HTTPException(400, "Deactivate the policy before deleting it.")
    await db.delete(p)
    await db.commit()

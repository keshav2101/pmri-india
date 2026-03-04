"""routers/settlements.py — Settlements admin router for PMRI India."""
from __future__ import annotations
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_admin_user
from app.models.user import User
from app.models.policy import Settlement, Policy
from app.models.org import OrgMember
from app.schemas.policy import SettlementResponse, SettlementRunResponse
from app.services.settlement_service import run_settlements

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.post("/run", response_model=SettlementRunResponse)
async def trigger_settlements(term: str = None, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    """Admin-only endpoint to manually trigger the settlement maturation cron job."""
    return await run_settlements(db, term)


@router.get("/{policy_id}", response_model=SettlementResponse)
async def get_settlement_for_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = (await db.execute(select(Settlement).where(Settlement.policy_id == uuid.UUID(policy_id)))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Settlement not found.")
        
    p = (await db.execute(select(Policy).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
    
    if p.org_id:
        m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == p.org_id, OrgMember.user_id == current_user.id))
        if not m_q.scalar_one_or_none() and not current_user.is_admin:
            raise HTTPException(403, "Access denied.")
    elif p.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied.")
        
    return SettlementResponse.model_validate(s)

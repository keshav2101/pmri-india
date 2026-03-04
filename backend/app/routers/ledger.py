"""routers/ledger.py — Ledger router for PMRI India."""
from __future__ import annotations
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.policy import LedgerTransaction, Policy
from app.models.org import OrgMember
from app.schemas.policy import LedgerTransactionResponse

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("", response_model=List[LedgerTransactionResponse])
async def list_transactions(policy_id: str = None, org_id: str = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = select(LedgerTransaction).options(selectinload(LedgerTransaction.policy))
    
    if policy_id:
        p = (await db.execute(select(Policy).where(Policy.id == uuid.UUID(policy_id)))).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Policy not found.")
        if p.org_id and not current_user.is_admin:
            m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == p.org_id, OrgMember.user_id == current_user.id))
            if not m_q.scalar_one_or_none():
                raise HTTPException(403, "Access denied.")
        elif not p.org_id and p.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "Access denied.")
        q = q.where(LedgerTransaction.policy_id == uuid.UUID(policy_id))
    elif org_id:
        if not current_user.is_admin:
            m_q = await db.execute(select(OrgMember).where(OrgMember.org_id == uuid.UUID(org_id), OrgMember.user_id == current_user.id))
            if not m_q.scalar_one_or_none():
                raise HTTPException(403, "Access denied.")
        q = q.join(Policy).where(Policy.org_id == uuid.UUID(org_id))
    else:
        q = q.join(Policy).where(Policy.user_id == current_user.id, Policy.org_id.is_(None))
        
    return (await db.execute(q.order_by(LedgerTransaction.created_at.desc()))).scalars().all()

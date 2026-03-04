"""routers/orgs.py — Org management router for PMRI India (institutional)."""
from __future__ import annotations
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org import Org, OrgMember
from app.schemas.org import OrgCreate, AddMemberRequest, OrgResponse, OrgMemberResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orgs", tags=["Orgs"])


def _org_response(org: Org, members: list) -> OrgResponse:
    return OrgResponse(
        id=str(org.id), name=org.name, tier=org.tier,
        created_at=org.created_at.isoformat(),
        members=[
            OrgMemberResponse(
                user_id=str(m.user_id), email=m.user.email if hasattr(m, 'user') and m.user else "—",
                role=m.role, joined_at=m.joined_at.isoformat()
            ) for m in members
        ],
    )


@router.post("", response_model=OrgResponse, status_code=201)
async def create_org(req: OrgCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check name unique
    existing = await db.execute(select(Org).where(Org.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail=f"Organisation '{req.name}' already exists.")
    org = Org(name=req.name, tier=req.tier)
    db.add(org)
    await db.flush()
    member = OrgMember(org_id=org.id, user_id=current_user.id, role="OWNER")
    db.add(member)
    await db.commit()
    await db.refresh(org)
    return _org_response(org, [member])


@router.get("", response_model=List[OrgResponse])
async def list_orgs(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List orgs the current user belongs to."""
    q = await db.execute(
        select(OrgMember).where(OrgMember.user_id == current_user.id)
    )
    memberships = q.scalars().all()
    result = []
    for m in memberships:
        org_q = await db.execute(select(Org).where(Org.id == m.org_id))
        org = org_q.scalar_one_or_none()
        if org:
            members_q = await db.execute(select(OrgMember).where(OrgMember.org_id == org.id))
            members = members_q.scalars().all()
            result.append(_org_response(org, members))
    return result


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(org_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = (await db.execute(select(Org).where(Org.id == uuid.UUID(org_id)))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, detail="Organisation not found.")
    # Check membership
    member_q = await db.execute(select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == current_user.id))
    if not member_q.scalar_one_or_none() and not current_user.is_admin:
        raise HTTPException(403, detail="Not a member of this organisation.")
    members_q = await db.execute(select(OrgMember).where(OrgMember.org_id == org.id))
    return _org_response(org, members_q.scalars().all())


@router.post("/{org_id}/members", response_model=OrgResponse)
async def add_member(org_id: str, req: AddMemberRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org = (await db.execute(select(Org).where(Org.id == uuid.UUID(org_id)))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, detail="Organisation not found.")
    # Only OWNER or admin can add members
    my_membership = (await db.execute(select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == current_user.id))).scalar_one_or_none()
    if (not my_membership or my_membership.role != "OWNER") and not current_user.is_admin:
        raise HTTPException(403, detail="Only org owners or admins can add members.")
    # Find target user
    target = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail=f"User '{req.email}' not found. They must register first.")
    # Check already a member
    existing_m = (await db.execute(select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == target.id))).scalar_one_or_none()
    if existing_m:
        raise HTTPException(400, detail="User is already a member of this organisation.")
    db.add(OrgMember(org_id=org.id, user_id=target.id, role=req.role))
    await db.commit()
    members_q = await db.execute(select(OrgMember).where(OrgMember.org_id == org.id))
    return _org_response(org, members_q.scalars().all())

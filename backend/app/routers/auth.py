"""routers/auth.py — Auth router for PMRI India (register, login, me)."""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org import Org, OrgMember
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new retail user or create an institutional org + owner."""
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    if req.account_type == "INSTITUTIONAL":
        if not req.org_name:
            raise HTTPException(status_code=400, detail="org_name is required for institutional registration.")
        # Check org name uniqueness
        existing_org = await db.execute(select(Org).where(Org.name == req.org_name))
        if existing_org.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Organisation '{req.org_name}' already exists.")
        tier = "INSTITUTIONAL_BASIC"
    else:
        tier = "RETAIL"

    user = User(email=req.email, hashed_password=hash_password(req.password), tier=tier)
    db.add(user)
    await db.flush()

    if req.account_type == "INSTITUTIONAL":
        org = Org(name=req.org_name, tier="INSTITUTIONAL_BASIC")
        db.add(org)
        await db.flush()
        db.add(OrgMember(org_id=org.id, user_id=user.id, role="OWNER"))

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "tier": user.tier, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token, user_id=str(user.id), email=user.email,
        tier=user.tier, is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token({"sub": str(user.id), "tier": user.tier, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token, user_id=str(user.id), email=user.email,
        tier=user.tier, is_admin=user.is_admin,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id), email=current_user.email, tier=current_user.tier,
        is_admin=current_user.is_admin, created_at=current_user.created_at.isoformat(),
    )

"""routers/rules.py — Admin tier rules config router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user, get_admin_user
from app.models.user import User
from app.models.policy import RulesConfig
from app.schemas.policy import RulesConfigResponse, RulesConfigUpdate

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get("/{tier}", response_model=RulesConfigResponse)
async def get_rules_for_tier(tier: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    tier = tier.strip().upper()
    r = (await db.execute(select(RulesConfig).where(RulesConfig.tier == tier))).scalar_one_or_none()
    if not r:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
        from pricing import DEFAULT_RULES
        default = DEFAULT_RULES.get(tier)
        if not default:
            raise HTTPException(404, detail=f"Tier {tier} not found.")
        return RulesConfigResponse(id="", tier=tier, config_json=default, updated_at="")
    return RulesConfigResponse.model_validate(r)


@router.put("/{tier}", response_model=RulesConfigResponse)
async def update_rules_for_tier(tier: str, req: RulesConfigUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    tier = tier.strip().upper()
    r = (await db.execute(select(RulesConfig).where(RulesConfig.tier == tier))).scalar_one_or_none()
    if r:
        r.config_json = req.config_json
        r.updated_by = admin.id
    else:
        r = RulesConfig(tier=tier, config_json=req.config_json, updated_by=admin.id)
        db.add(r)
    await db.commit()
    await db.refresh(r)
    return RulesConfigResponse.model_validate(r)

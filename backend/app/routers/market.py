"""routers/market.py — Market router for PMRI."""
from __future__ import annotations
import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import get_current_user
from app.models.user import User
from app.services.market_service import market_service

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/universe")
async def get_universe(current_user: User = Depends(get_current_user)):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
    from symbols import _load_universe
    universe = _load_universe()
    return {"supported_exchanges": list(universe.keys()), "universe": universe}


@router.get("/prices/{symbol}/current")
async def get_current_price(symbol: str, current_user: User = Depends(get_current_user)):
    try:
        price = market_service.get_current_price(symbol.upper())
        return {"symbol": symbol.upper(), "price_inr": price}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

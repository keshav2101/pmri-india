"""routers/market.py — Market data router for PMRI."""
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
    return {
        "supported_exchanges": list(universe.keys()),
        "universe": universe,
        "data_source": market_service.data_source,
    }


@router.get("/prices/{symbol}/current")
async def get_current_price(symbol: str, current_user: User = Depends(get_current_user)):
    try:
        price = market_service.get_current_price(symbol.upper())
        return {
            "symbol": symbol.upper(),
            "price": price,
            "price_inr": price,          # kept for backwards compat
            "data_source": market_service.data_source,
            "provider": market_service.provider,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/prices/{symbol}/history")
async def get_price_history(
    symbol: str,
    days: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Get trailing N days of closing prices for charts."""
    try:
        prices = market_service.get_historical_prices(symbol.upper(), days=days)
        return {
            "symbol": symbol.upper(),
            "days": len(prices),
            "prices": prices,
            "data_source": market_service.data_source,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/status")
async def market_status(current_user: User = Depends(get_current_user)):
    """Returns current market data provider status."""
    return {
        "provider": market_service.provider,
        "data_source": market_service.data_source,
        "symbols_covered": len(market_service.symbols),
        "symbols": market_service.symbols,
    }

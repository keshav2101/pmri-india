"""services/market_service.py — Unified India/US market data service (demo CSV) with forward-fill."""
from __future__ import annotations
import csv
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MarketService:
    def __init__(self):
        self.prices: Dict[str, Dict[date, float]] = {}  # symbol -> {date: close_price}
        self.last_close: Dict[str, float] = {}
        self.symbols: List[str] = []
        if settings.demo_mode:
            self._load_demo_data()

    def _load_demo_data(self):
        ml_data_dir = Path(settings.ml_module_path) / "data"
        if not ml_data_dir.exists():
            logger.warning("ML data dir not found at %s", ml_data_dir)
            return

        for csv_path in ml_data_dir.glob("*.csv"):
            if "universe" in csv_path.name: continue
            sym = csv_path.stem  # e.g. RELIANCE.NSE, AAPL.NASDAQ
            self.prices[sym] = {}
            with open(csv_path, newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        d = date.fromisoformat(row["date"].split("T")[0])
                        close = float(row["close"])
                        self.prices[sym][d] = close
                        self.last_close[sym] = close
                    except (KeyError, ValueError):
                        pass
            self.symbols.append(sym)
        logger.info("Loaded demo prices for %d symbols", len(self.symbols))

    def get_current_price(self, symbol: str) -> float:
        """Get latest available price."""
        if symbol not in self.prices:
            raise ValueError(f"No market data for {symbol}")
        return self.last_close.get(symbol, 0.0)

    def get_price_on(self, symbol: str, target_date: date) -> float:
        """Get price on date. If missing (holiday/weekend), forward-fill from previous."""
        if symbol not in self.prices:
            raise ValueError(f"No market data for {symbol}")
        
        # Max lookback 10 days
        for i in range(10):
            d = target_date - timedelta(days=i)
            if d in self.prices[symbol]:
                return self.prices[symbol][d]
        raise ValueError(f"No recent price found for {symbol} on/before {target_date}")

    def get_historical_prices(self, symbol: str, days: int = 100) -> List[float]:
        """Get trailing N days of prices up to last close."""
        if symbol not in self.prices:
            raise ValueError(f"No market data for {symbol}")
        
        sorted_dates = sorted(self.prices[symbol].keys())
        recent = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
        return [self.prices[symbol][d] for d in recent]


market_service = MarketService()

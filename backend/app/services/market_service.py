"""services/market_service.py — Unified market data service with live Yahoo Finance + demo CSV fallback."""
from __future__ import annotations

import csv
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Symbol mapping: internal PMRI format → Yahoo Finance ticker
# NSE stocks use .NS suffix, NASDAQ stocks use bare tickers
# ---------------------------------------------------------------------------
_YF_SYMBOL_MAP: Dict[str, str] = {
    # NSE
    "RELIANCE.NSE":    "RELIANCE.NS",
    "TCS.NSE":         "TCS.NS",
    "HDFCBANK.NSE":    "HDFCBANK.NS",
    "INFY.NSE":        "INFY.NS",
    "ICICIBANK.NSE":   "ICICIBANK.NS",
    "HINDUNILVR.NSE":  "HINDUNILVR.NS",
    "SBIN.NSE":        "SBIN.NS",
    "BHARTIARTL.NSE":  "BHARTIARTL.NS",
    "ITC.NSE":         "ITC.NS",
    "WIPRO.NSE":       "WIPRO.NS",
    # NASDAQ
    "AAPL.NASDAQ":     "AAPL",
    "MSFT.NASDAQ":     "MSFT",
    "GOOGL.NASDAQ":    "GOOGL",
    "TSLA.NASDAQ":     "TSLA",
    "AMZN.NASDAQ":     "AMZN",
    "NVDA.NASDAQ":     "NVDA",
    "META.NASDAQ":     "META",
}

# Cache: symbol → (price, timestamp)
_PRICE_CACHE: Dict[str, Tuple[float, float]] = {}
_HIST_CACHE:  Dict[str, Tuple[List[float], float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour cache to stay within Yahoo Finance limits


def _to_yf_ticker(symbol: str) -> str:
    """Convert internal PMRI symbol to Yahoo Finance ticker."""
    return _YF_SYMBOL_MAP.get(symbol.upper(), symbol.split(".")[0] + ".NS")


def _fetch_live_price(symbol: str) -> Optional[float]:
    """Fetch current price from Yahoo Finance with 1-hour caching."""
    now = time.time()
    cached = _PRICE_CACHE.get(symbol)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        logger.debug("Cache hit for %s price: %.2f", symbol, cached[0])
        return cached[0]

    yf_ticker = _to_yf_ticker(symbol)
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_ticker)
        info = ticker.fast_info
        price = float(info.last_price or info.previous_close or 0)
        if price and price > 0:
            _PRICE_CACHE[symbol] = (price, now)
            logger.info("Live price fetched for %s (%s): %.2f", symbol, yf_ticker, price)
            return price
        logger.warning("Yahoo Finance returned zero/null price for %s", yf_ticker)
    except Exception as e:
        logger.error("Yahoo Finance price fetch failed for %s: %s", yf_ticker, e)
    return None


def _fetch_live_history(symbol: str, days: int = 100) -> Optional[List[float]]:
    """Fetch historical closing prices from Yahoo Finance with 1-hour caching."""
    cache_key = f"{symbol}:{days}"
    now = time.time()
    cached = _HIST_CACHE.get(cache_key)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    yf_ticker = _to_yf_ticker(symbol)
    try:
        import yfinance as yf
        # Fetch extra days to account for weekends/holidays
        period = f"{min(days + 30, 365)}d"
        hist = yf.Ticker(yf_ticker).history(period=period)
        if hist.empty:
            logger.warning("Yahoo Finance returned empty history for %s", yf_ticker)
            return None
        closes = hist["Close"].dropna().tolist()[-days:]
        if closes:
            _HIST_CACHE[cache_key] = (closes, now)
            logger.info("Live history fetched for %s (%s): %d rows", symbol, yf_ticker, len(closes))
            return closes
    except Exception as e:
        logger.error("Yahoo Finance history fetch failed for %s: %s", yf_ticker, e)
    return None


class MarketService:
    """Market data service — live Yahoo Finance with demo CSV fallback."""

    def __init__(self):
        self.provider = settings.market_provider.lower()  # "live" or "demo"
        # Demo / fallback data
        self._demo_prices: Dict[str, Dict[date, float]] = {}
        self._demo_last_close: Dict[str, float] = {}
        self._demo_symbols: List[str] = []
        self._load_demo_data()  # always load demo as fallback
        logger.info("MarketService initialised — provider: %s", self.provider)

    # ------------------------------------------------------------------
    # Demo CSV loader (fallback)
    # ------------------------------------------------------------------
    def _load_demo_data(self):
        ml_data_dir = Path(settings.ml_module_path) / "data"
        if not ml_data_dir.exists():
            logger.warning("ML data dir not found at %s — demo fallback unavailable", ml_data_dir)
            return
        for csv_path in ml_data_dir.glob("*.csv"):
            if "universe" in csv_path.name:
                continue
            sym = csv_path.stem
            self._demo_prices[sym] = {}
            with open(csv_path, newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        d = date.fromisoformat(row["date"].split("T")[0])
                        close = float(row["close"])
                        self._demo_prices[sym][d] = close
                        self._demo_last_close[sym] = close
                    except (KeyError, ValueError):
                        pass
            self._demo_symbols.append(sym)
        logger.info("Demo fallback loaded for %d symbols", len(self._demo_symbols))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def symbols(self) -> List[str]:
        if self.provider == "live":
            return list(_YF_SYMBOL_MAP.keys())
        return self._demo_symbols

    @property
    def data_source(self) -> str:
        return "Yahoo Finance (Live)" if self.provider == "live" else "Demo CSV"

    def get_current_price(self, symbol: str) -> float:
        """Get latest price — live first, demo fallback."""
        if self.provider == "live":
            price = _fetch_live_price(symbol)
            if price:
                return price
            logger.warning("Live price unavailable for %s, using demo fallback", symbol)

        # Demo fallback
        if symbol not in self._demo_last_close:
            raise ValueError(f"No market data for symbol '{symbol}'")
        return self._demo_last_close[symbol]

    def get_price_on(self, symbol: str, target_date: date) -> float:
        """Get price on a specific date (used for settlement). Always uses demo CSV."""
        if symbol not in self._demo_prices:
            raise ValueError(f"No historical data for '{symbol}'")
        for i in range(10):
            d = target_date - timedelta(days=i)
            if d in self._demo_prices[symbol]:
                return self._demo_prices[symbol][d]
        raise ValueError(f"No recent price for '{symbol}' on/before {target_date}")

    def get_historical_prices(self, symbol: str, days: int = 100) -> List[float]:
        """Get trailing N days of closing prices for volatility/ML calc."""
        if self.provider == "live":
            prices = _fetch_live_history(symbol, days)
            if prices:
                return prices
            logger.warning("Live history unavailable for %s, using demo fallback", symbol)

        if symbol not in self._demo_prices:
            raise ValueError(f"No market data for '{symbol}'")
        sorted_dates = sorted(self._demo_prices[symbol].keys())
        recent = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
        return [self._demo_prices[symbol][d] for d in recent]


market_service = MarketService()

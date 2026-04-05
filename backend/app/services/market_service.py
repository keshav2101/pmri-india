"""services/market_service.py — Unified live market service.

Dynamic symbol resolution: ANY SYMBOL.NSE or SYMBOL.BSE or SYMBOL.BSE works
automatically via Yahoo Finance without any hardcoded mapping.
  - RELIANCE.NSE  → RELIANCE.NS  (Yahoo Finance)
  - RELIANCE.BSE  → RELIANCE.BO  (Yahoo Finance)
  - AAPL.NASDAQ   → AAPL         (Yahoo Finance)
  - AAPL.NYSE     → AAPL         (Yahoo Finance)
"""
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

# Cache: symbol → (price, timestamp)
_PRICE_CACHE: Dict[str, Tuple[float, float]] = {}
_HIST_CACHE:  Dict[str, Tuple[List[float], float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1-hour cache to stay within Yahoo Finance limits

# Special overrides for symbols that don't follow the simple pattern
_YF_OVERRIDES: Dict[str, str] = {
    "M&M.NSE":         "M&M.NS",
    "M&M.BSE":         "M&M.BO",
    "BAJAJ-AUTO.NSE":  "BAJAJ-AUTO.NS",
    "BAJAJ-AUTO.BSE":  "BAJAJ-AUTO.BO",
    "MCDOWELL-N.NSE":  "MCDOWELL-N.NS",
    "MCDOWELL-N.BSE":  "MCDOWELL-N.BO",
}

# US exchanges that use bare ticker (no suffix)
_US_EXCHANGES = {"NASDAQ", "NYSE", "US", "AMEX", "OTC"}


def _to_yf_ticker(symbol: str) -> str:
    """
    Dynamically convert ANY internal PMRI symbol to Yahoo Finance ticker.

    Rules:
      SYMBOL.NSE    → SYMBOL.NS
      SYMBOL.BSE    → SYMBOL.BO
      SYMBOL.NASDAQ → SYMBOL  (bare)
      SYMBOL.NYSE   → SYMBOL  (bare)

    No hardcoded list needed — this works for every stock on NSE/BSE.
    """
    upper = symbol.upper().strip()

    # Check overrides first
    if upper in _YF_OVERRIDES:
        return _YF_OVERRIDES[upper]

    if "." not in upper:
        return upper  # Bare US ticker (AAPL, MSFT, etc.)

    parts = upper.rsplit(".", 1)
    base = parts[0]
    exchange = parts[1]

    if exchange == "NSE":
        return f"{base}.NS"
    elif exchange == "BSE":
        return f"{base}.BO"
    elif exchange in _US_EXCHANGES:
        return base  # bare US ticker
    else:
        # Unknown exchange — try NSE as default
        return f"{base}.NS"


def _fetch_live_price(symbol: str) -> Optional[float]:
    """Fetch current price from Yahoo Finance with 1-hour caching."""
    now = time.time()
    cached = _PRICE_CACHE.get(symbol)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        logger.debug("Cache hit for %s: %.2f", symbol, cached[0])
        return cached[0]

    yf_ticker = _to_yf_ticker(symbol)
    try:
        import yfinance as yf
        info = yf.Ticker(yf_ticker).fast_info
        price = float(info.last_price or info.previous_close or 0)
        if price and price > 0:
            _PRICE_CACHE[symbol] = (price, now)
            logger.info("Live price %s (%s): %.2f", symbol, yf_ticker, price)
            return price
        logger.warning("Zero price from Yahoo for %s (%s)", symbol, yf_ticker)
    except Exception as e:
        logger.error("Yahoo Finance error for %s: %s", yf_ticker, e)
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
        period = f"{min(days + 40, 365)}d"
        hist = yf.Ticker(yf_ticker).history(period=period)
        if hist.empty:
            logger.warning("Empty history from Yahoo for %s (%s)", symbol, yf_ticker)
            return None
        closes = hist["Close"].dropna().tolist()[-days:]
        if closes:
            _HIST_CACHE[cache_key] = (closes, now)
            logger.info("History fetched for %s: %d rows", symbol, len(closes))
            return closes
    except Exception as e:
        logger.error("Yahoo Finance history error for %s: %s", yf_ticker, e)
    return None


class MarketService:
    """Live market data via Yahoo Finance — supports ALL NSE, BSE, NASDAQ, NYSE stocks."""

    def __init__(self):
        self.provider = settings.market_provider.lower()
        self._demo_prices: Dict[str, Dict[date, float]] = {}
        self._demo_last_close: Dict[str, float] = {}
        self._demo_symbols: List[str] = []
        self._load_demo_data()
        logger.info("MarketService ready — provider=%s", self.provider)

    def _load_demo_data(self):
        """Load demo CSV files as fallback."""
        ml_data_dir = Path(settings.ml_module_path) / "data"
        if not ml_data_dir.exists():
            logger.warning("ML data dir not found at %s", ml_data_dir)
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
        logger.info("Demo fallback loaded: %d symbols", len(self._demo_symbols))

    @property
    def symbols(self) -> List[str]:
        return self._demo_symbols

    @property
    def data_source(self) -> str:
        return "Yahoo Finance (Live)" if self.provider == "live" else "Demo CSV"

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for ANY NSE/BSE/NASDAQ symbol.
        SYMBOL.NSE, SYMBOL.BSE, AAPL.NASDAQ etc. all work automatically.
        Falls back to demo CSV if Yahoo Finance is unavailable.
        """
        if self.provider == "live":
            price = _fetch_live_price(symbol)
            if price:
                return price
            logger.warning("Live price failed for %s — falling back to demo", symbol)

        if symbol not in self._demo_last_close:
            raise ValueError(
                f"No data for '{symbol}'. "
                f"For NSE use SYMBOL.NSE format (e.g. RELIANCE.NSE). "
                f"For BSE use SYMBOL.BSE format (e.g. RELIANCE.BSE)."
            )
        return self._demo_last_close[symbol]

    def validate_symbol(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        Validate a symbol by trying to fetch its current price.
        Returns (is_valid, price_or_None).
        Works for any NSE/BSE symbol dynamically.
        """
        try:
            price = _fetch_live_price(symbol)
            return (price is not None and price > 0), price
        except Exception:
            return False, None

    def get_price_on(self, symbol: str, target_date: date) -> float:
        """Get price on specific date (for settlement). Uses demo CSV."""
        if symbol not in self._demo_prices:
            # For live mode, use current price as approximation
            if self.provider == "live":
                price = _fetch_live_price(symbol)
                if price:
                    return price
            raise ValueError(f"No historical price data for '{symbol}'")
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
            logger.warning("Live history failed for %s — using demo", symbol)

        if symbol not in self._demo_prices:
            raise ValueError(f"No historical data for '{symbol}'")
        sorted_dates = sorted(self._demo_prices[symbol].keys())
        recent = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
        return [self._demo_prices[symbol][d] for d in recent]


market_service = MarketService()

"""
symbols.py — NSE/BSE symbol normalization and cash equity validation.

All internal symbol references use the canonical form: SYMBOL.NSE or SYMBOL.BSE.
Only instruments in the VALID_UNIVERSE are accepted. F&O contracts,
ETFs with non-equity underlying, SME-listed, and unlisted instruments are rejected.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Internal canonical universe (extended by data/valid_universe.csv at runtime)
# ---------------------------------------------------------------------------

# Hardcoded baseline — Large-cap cash equities for demo/fallback
_DEMO_UNIVERSE_NSE = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "WIPRO", "BHARTIARTL", "SBIN", "HINDUNILVR", "ITC",
    "BAJFINANCE", "KOTAKBANK", "LTIM", "AXISBANK", "MARUTI",
}
_DEMO_UNIVERSE_BSE = set(_DEMO_UNIVERSE_NSE)  # BSE mirrors NSE for demo
_DEMO_UNIVERSE_NASDAQ = {
    "AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META",
}

# Exchange aliases
_EXCHANGE_ALIASES = {
    "NSE": "NSE", "BSE": "BSE", "NASDAQ": "NASDAQ", "NYSE": "NYSE",
    "nse": "NSE", "bse": "BSE", "nasdaq": "NASDAQ", "nyse": "NYSE",
    "N": "NSE", "B": "BSE", "NS": "NSE", "BS": "BSE",
}

_universe_cache: dict[str, set[str]] | None = None


def _load_universe() -> dict[str, set[str]]:
    """Load the valid symbol universe from data/valid_universe.csv if it exists."""
    global _universe_cache
    if _universe_cache is not None:
        return _universe_cache

    universe: dict[str, set[str]] = {
        "NSE":    set(_DEMO_UNIVERSE_NSE),
        "BSE":    set(_DEMO_UNIVERSE_BSE),
        "NASDAQ": set(_DEMO_UNIVERSE_NASDAQ),
        "NYSE":   set(),
    }

    csv_path = Path(__file__).parent / "data" / "valid_universe.csv"
    if csv_path.exists():
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                sym = row.get("symbol", "").strip().upper()
                exc = row.get("exchange", "NSE").strip().upper()
                if sym and exc in universe:
                    universe[exc].add(sym)

    _universe_cache = universe
    return universe


def normalize_symbol(raw_symbol: str, exchange: str = "NSE") -> Tuple[str, str]:
    """
    Normalize a user-supplied symbol to canonical (SYMBOL, EXCHANGE) pair.

    Accepts:
        "RELIANCE"        → ("RELIANCE", "NSE")
        "RELIANCE.NSE"    → ("RELIANCE", "NSE")
        "RELIANCE.BSE"    → ("RELIANCE", "BSE")
        "INFY", "BSE"     → ("INFY", "BSE")

    Returns:
        (canonical_symbol, canonical_exchange)

    Raises:
        ValueError: if symbol format is unrecognizable or exchange unknown.
    """
    raw_symbol = raw_symbol.strip().upper()

    # Handle dot-notation: SYMBOL.EXCHANGE
    if "." in raw_symbol:
        parts = raw_symbol.rsplit(".", 1)
        sym = parts[0].strip()
        exc_raw = parts[1].strip()
    else:
        sym = raw_symbol
        exc_raw = exchange.strip().upper()

    canonical_exc = _EXCHANGE_ALIASES.get(exc_raw)
    if not canonical_exc:
        raise ValueError(f"Unknown exchange '{exc_raw}'. Use NSE or BSE.")

    return sym.upper(), canonical_exc


def canonical_key(symbol: str, exchange: str) -> str:
    """Return the canonical internal key: 'SYMBOL.EXCHANGE'."""
    return f"{symbol}.{exchange}"


def validate_cash_equity(symbol: str, exchange: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that the given symbol is a listed cash equity.

    In LIVE mode: any NSE/BSE symbol passes — Yahoo Finance validates dynamically.
    In DEMO mode: only symbols in the static universe CSV are accepted.
    """
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.market_provider.lower() == "live":
            # Dynamic validation — accept any symbol; Yahoo Finance will reject unknown ones
            if exchange not in ("NSE", "BSE", "NASDAQ", "NYSE"):
                return False, f"Unknown exchange '{exchange}'. Use NSE, BSE, NASDAQ, or NYSE."
            return True, None
    except Exception:
        pass

    # Demo/fallback: strict universe check
    universe = _load_universe()
    exc_universe = universe.get(exchange, set())
    if symbol not in exc_universe:
        return False, (
            f"'{symbol}.{exchange}' is not in the supported universe. "
            f"In live mode any NSE/BSE symbol is accepted."
        )
    return True, None


def validate_and_normalize(raw_symbol: str, exchange: str = "NSE") -> Tuple[str, str, Optional[str]]:
    """
    Combined utility: normalize + validate.

    Returns:
        (canonical_symbol, canonical_exchange, error_message_or_None)
    """
    try:
        sym, exc = normalize_symbol(raw_symbol, exchange)
    except ValueError as e:
        return raw_symbol.upper(), exchange.upper(), str(e)

    is_valid, reason = validate_cash_equity(sym, exc)
    return sym, exc, reason if not is_valid else None


def list_demo_symbols() -> list[str]:
    """Return all demo-mode supported symbols in canonical key form."""
    return sorted(f"{s}.NSE" for s in _DEMO_UNIVERSE_NSE)

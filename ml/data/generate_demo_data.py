"""
data/generate_demo_data.py — Generate synthetic NSE OHLCV price data for demo mode.

Produces 8 tickers × 5 years of daily data using seeded Geometric Brownian Motion.
Also generates valid_universe.csv — the cash equity symbol registry.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from math import exp, log, sqrt
from pathlib import Path

# ─── Config ─────────────────────────────────────────────────────────────────

TICKERS = {
    # NSE
    "RELIANCE":   (2800.0, 0.14, 0.26, 1001, "NSE"),
    "TCS":        (3600.0, 0.12, 0.22, 1002, "NSE"),
    "INFY":       (1450.0, 0.13, 0.24, 1003, "NSE"),
    "HDFCBANK":   (1620.0, 0.11, 0.20, 1004, "NSE"),
    "ICICIBANK":  (980.0,  0.15, 0.28, 1005, "NSE"),
    "WIPRO":      (460.0,  0.10, 0.26, 1006, "NSE"),
    "BHARTIARTL": (1200.0, 0.16, 0.30, 1007, "NSE"),
    "SBIN":       (620.0,  0.13, 0.32, 1008, "NSE"),
    # NASDAQ
    "AAPL":       (150.0,  0.18, 0.25, 2001, "NASDAQ"),
    "MSFT":       (300.0,  0.20, 0.22, 2002, "NASDAQ"),
    "GOOGL":      (100.0,  0.15, 0.28, 2003, "NASDAQ"),
    "TSLA":       (200.0,  0.25, 0.45, 2004, "NASDAQ"),
}

NSE_MARKET_HOLIDAYS_2024_2025 = {
    # 2024
    date(2024, 1, 26), date(2024, 3, 25), date(2024, 3, 29), date(2024, 4, 14),
    date(2024, 4, 17), date(2024, 5, 1),  date(2024, 6, 17), date(2024, 7, 17),
    date(2024, 8, 15), date(2024, 10, 2), date(2024, 11, 1), date(2024, 11, 15),
    date(2024, 12, 25),
    # 2025
    date(2025, 1, 26), date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31),
    date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1),  date(2025, 8, 15),
    date(2025, 10, 2), date(2025, 10, 23), date(2025, 11, 5), date(2025, 12, 25),
}


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in NSE_MARKET_HOLIDAYS_2024_2025


def generate_gbm_prices(
    base: float, drift: float, vol: float, n_days: int, seed: int
) -> list[float]:
    """Simulate daily closing prices using GBM."""
    rng = random.Random(seed)
    dt = 1 / 252
    prices = [base]
    for _ in range(n_days - 1):
        z = rng.gauss(0, 1)
        r = (drift - 0.5 * vol ** 2) * dt + vol * sqrt(dt) * z
        prices.append(round(prices[-1] * exp(r), 2))
    return prices


def trading_days_range(start: date, end: date) -> list[date]:
    day, days = start, []
    while day <= end:
        if is_trading_day(day):
            days.append(day)
        day += timedelta(days=1)
    return days


def generate_ohlcv(close: float, prev_close: float, seed_offset: int, rng: random.Random) -> dict:
    """Generate realistic OHLCV from close price."""
    daily_range = close * rng.uniform(0.008, 0.025)
    high = round(close + daily_range * rng.uniform(0.3, 1.0), 2)
    low  = round(close - daily_range * rng.uniform(0.3, 1.0), 2)
    open_ = round(prev_close * (1 + rng.gauss(0, 0.004)), 2)
    vol  = int(rng.uniform(500_000, 5_000_000))
    return {"open": open_, "high": max(high, open_, close), "low": min(low, open_, close), "volume": vol}


def main():
    out_dir = Path(__file__).parent
    out_dir.mkdir(exist_ok=True)

    end_date   = date(2025, 3, 3)
    start_date = date(2020, 3, 4)
    tdays      = trading_days_range(start_date, end_date)
    n          = len(tdays)

    print(f"Generating {n} trading days ({start_date} → {end_date}) for {len(TICKERS)} tickers…")

    for ticker, (base, drift, vol, seed, exchange) in TICKERS.items():
        closes = generate_gbm_prices(base, drift, vol, n, seed)
        rng    = random.Random(seed + 9999)
        rows   = []

        for i, (d, close) in enumerate(zip(tdays, closes)):
            prev_close = closes[i - 1] if i > 0 else base
            ohlcv      = generate_ohlcv(close, prev_close, i, rng)
            rows.append({
                "date": d.isoformat(),
                "open": ohlcv["open"], "high": ohlcv["high"],
                "low": ohlcv["low"],   "close": round(close, 2),
                "volume": ohlcv["volume"],
            })

        filepath = out_dir / f"{ticker}.{exchange}.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"  ✓ {filepath.name} ({n} rows, last close: ₹{rows[-1]['close']:,.2f})")

    # Generate valid_universe.csv
    universe_path = out_dir / "valid_universe.csv"
    with open(universe_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "exchange", "instrument_type", "sector"])
        writer.writeheader()
        
        # NSE Tickers
        nse_sectors = {
            "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT", "HDFCBANK": "Banking",
            "ICICIBANK": "Banking", "WIPRO": "IT", "BHARTIARTL": "Telecom", "SBIN": "Banking",
            "HINDUNILVR": "FMCG", "ITC": "FMCG", "BAJFINANCE": "NBFC",
            "KOTAKBANK": "Banking", "LTIM": "IT", "AXISBANK": "Banking", "MARUTI": "Auto",
        }
        for sym, sector in nse_sectors.items():
            writer.writerow({"symbol": sym, "exchange": "NSE", "instrument_type": "EQ", "sector": sector})
            writer.writerow({"symbol": sym, "exchange": "BSE", "instrument_type": "EQ", "sector": sector})
            
        # NASDAQ Tickers
        nasdaq_sectors = {
            "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "TSLA": "Auto",
        }
        for sym, sector in nasdaq_sectors.items():
            writer.writerow({"symbol": sym, "exchange": "NASDAQ", "instrument_type": "EQ", "sector": sector})
            
    print(f"  ✓ {universe_path.name} ({len(nse_sectors) * 2 + len(nasdaq_sectors)} entries)")

    print("Done!")


if __name__ == "__main__":
    main()

"""
features.py — Feature engineering for NSE/BSE portfolio risk model.

Computes:
  1. Per-stock features (rolling vol, max drawdown, skewness, kurtosis, mean return, vol ratio)
  2. Portfolio-level aggregation (weighted returns, correlation-adjusted portfolio vol)
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, List, Tuple


# ─── Per-Stock Features ──────────────────────────────────────────────────────

def _returns(prices: list[float]) -> list[float]:
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


def _rolling_vol(rets: list[float], window: int = 20) -> float:
    if len(rets) < window:
        return statistics.stdev(rets) * math.sqrt(252) if len(rets) >= 2 else 0.30
    window_rets = rets[-window:]
    return statistics.stdev(window_rets) * math.sqrt(252)


def _max_drawdown(prices: list[float]) -> float:
    peak, max_dd = prices[0], 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _skewness(rets: list[float]) -> float:
    n = len(rets)
    if n < 3:
        return 0.0
    mean = statistics.mean(rets)
    std  = statistics.stdev(rets)
    if std == 0:
        return 0.0
    return sum(((r - mean) / std) ** 3 for r in rets) / n


def _kurtosis(rets: list[float]) -> float:
    n = len(rets)
    if n < 4:
        return 0.0
    mean = statistics.mean(rets)
    std  = statistics.stdev(rets)
    if std == 0:
        return 0.0
    return sum(((r - mean) / std) ** 4 for r in rets) / n - 3  # excess kurtosis


def compute_stock_features(prices: list[float], window: int = 20) -> dict:
    """Compute 7 single-stock features from a list of daily close prices."""
    if len(prices) < 5:
        return {
            "rolling_vol": 0.30, "max_drawdown": 0.0, "skewness": 0.0,
            "kurtosis": 0.0, "mean_return": 0.0, "vol_ratio": 1.0, "last_price": prices[-1] if prices else 0.0,
        }

    rets          = _returns(prices)
    short_vol     = _rolling_vol(rets, min(10, len(rets)))
    long_vol      = _rolling_vol(rets, window)
    mean_ret      = statistics.mean(rets) if rets else 0.0

    return {
        "rolling_vol":  round(long_vol, 6),
        "max_drawdown": round(_max_drawdown(prices), 6),
        "skewness":     round(_skewness(rets), 6),
        "kurtosis":     round(_kurtosis(rets), 6),
        "mean_return":  round(mean_ret * 252, 6),   # annualized
        "vol_ratio":    round(short_vol / long_vol, 6) if long_vol > 0 else 1.0,
        "last_price":   prices[-1],
    }


def build_feature_matrix(
    symbols: list[str],
    prices_map: Dict[str, list[float]],
    term_days: int = 30,
) -> Tuple[list[dict], list[float]]:
    """
    Build per-stock feature dicts and tail-loss labels for training.

    A label is 1 if the stock drops more than 5% over the next `term_days`.
    Returns (feature_rows, labels).
    """
    feature_rows, labels = [], []
    for sym in symbols:
        prices = prices_map.get(sym, [])
        if len(prices) < term_days + 21:
            continue
        for i in range(20, len(prices) - term_days):
            historical = prices[:i]
            future_ret = (prices[i + term_days - 1] - prices[i]) / prices[i]
            feats      = compute_stock_features(historical, window=20)
            feats["term_days"] = term_days
            feature_rows.append(feats)
            labels.append(1 if future_ret < -0.05 else 0)

    return feature_rows, labels


# ─── Portfolio Aggregation ───────────────────────────────────────────────────

def pearson_correlation(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation between two return series."""
    n = min(len(xs), len(ys))
    if n < 5:
        return 0.5   # conservative mid-range if insufficient data
    xs, ys = xs[-n:], ys[-n:]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov    = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
    std_x  = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / n)
    std_y  = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / n)
    if std_x == 0 or std_y == 0:
        return 0.5
    return max(-1.0, min(1.0, cov / (std_x * std_y)))


def compute_portfolio_features(
    holdings: list[dict],            # [{"symbol": str, "weight": float, "prices": list[float]}]
    term_days: int = 30,
) -> dict:
    """
    Aggregate per-stock features to portfolio level.

    Args:
        holdings: list of dicts with symbol, weight (0-1), and prices list.
        term_days: policy term in days.

    Returns:
        Portfolio-level feature dict including correlation-adjusted vol.
    """
    if not holdings:
        return {
            "portfolio_vol": 0.30, "max_weight": 0.0, "avg_max_drawdown": 0.0,
            "weighted_mean_return": 0.0, "n_stocks": 0, "term_days": term_days,
            "herfindahl_index": 1.0,
        }

    stock_features: list[dict] = []
    stock_rets:     list[list[float]] = []

    for h in holdings:
        sf    = compute_stock_features(h["prices"], window=20)
        sf["weight"]  = h["weight"]
        sf["symbol"]  = h["symbol"]
        sf["term_days"] = term_days
        stock_features.append(sf)
        stock_rets.append(_returns(h["prices"]))

    # Correlation-adjusted portfolio vol
    n = len(holdings)
    portfolio_var = 0.0
    for i in range(n):
        for j in range(n):
            w_i   = holdings[i]["weight"]
            w_j   = holdings[j]["weight"]
            vol_i = stock_features[i]["rolling_vol"]
            vol_j = stock_features[j]["rolling_vol"]
            rho   = 1.0 if i == j else pearson_correlation(stock_rets[i], stock_rets[j])
            portfolio_var += w_i * w_j * vol_i * vol_j * rho

    portfolio_vol = math.sqrt(max(portfolio_var, 0.0))

    # Weighted mean daily return (annualized)
    weighted_mean_return = sum(
        h["weight"] * sf["mean_return"] for h, sf in zip(holdings, stock_features)
    )

    avg_max_drawdown = sum(
        h["weight"] * sf["max_drawdown"] for h, sf in zip(holdings, stock_features)
    )

    weights       = [h["weight"] for h in holdings]
    max_weight    = max(weights)
    herfindahl    = sum(w ** 2 for w in weights)  # concentration index

    return {
        "portfolio_vol":         round(portfolio_vol, 6),
        "max_weight":            round(max_weight, 6),
        "avg_max_drawdown":      round(avg_max_drawdown, 6),
        "weighted_mean_return":  round(weighted_mean_return, 6),
        "n_stocks":              n,
        "term_days":             term_days,
        "herfindahl_index":      round(herfindahl, 6),
        "stock_features":        stock_features,
    }

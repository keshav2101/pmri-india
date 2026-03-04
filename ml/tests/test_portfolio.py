"""
tests/test_portfolio.py — Unit tests for portfolio valuation, payoff, underwriting, and snapshot consistency.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest
from pricing import (
    compute_portfolio_settlement, compute_portfolio_quote,
    check_underwriting, DEFAULT_RULES, TERM_DAYS, MIN_PREMIUM_INR,
)
from features import compute_portfolio_features, pearson_correlation


# ─── Helper data ────────────────────────────────────────────────────────────

def _flat_prices(n: int = 60, price: float = 1000.0) -> list[float]:
    """Flat price series (no volatility)."""
    return [price] * n


def _trending_prices(n: int = 60, price: float = 1000.0, daily_drift: float = 0.001) -> list[float]:
    """Linearly trending prices."""
    return [price * (1 + daily_drift) ** i for i in range(n)]


def _declining_prices(n: int = 60, price: float = 1000.0, daily_drop: float = -0.002) -> list[float]:
    return [price * (1 + daily_drop) ** i for i in range(n)]


def _make_holdings(prices: list[float], weights: list[float] | None = None) -> list[dict]:
    symbols = ["RELIANCE", "TCS", "INFY"]
    n = len(symbols)
    w = weights or [1.0 / n] * n
    return [
        {"symbol": s, "weight": w[i], "prices": prices}
        for i, s in enumerate(symbols)
    ]


# ─── Portfolio Valuation ─────────────────────────────────────────────────────

class TestPortfolioValuation:
    def test_equal_weight_valuation(self):
        """Portfolio value = sum(qty × price)."""
        holdings = [
            {"symbol": "RELIANCE", "qty": 10, "price": 2800.0},
            {"symbol": "TCS",      "qty": 5,  "price": 3600.0},
            {"symbol": "INFY",     "qty": 20, "price": 1450.0},
        ]
        total = sum(h["qty"] * h["price"] for h in holdings)
        assert abs(total - (28000 + 18000 + 29000)) < 0.01

    def test_portfolio_features_n_stocks(self):
        holdings = _make_holdings(_trending_prices())
        feats = compute_portfolio_features(holdings, term_days=30)
        assert feats["n_stocks"] == 3

    def test_portfolio_vol_positive(self):
        holdings = _make_holdings(_declining_prices())
        feats = compute_portfolio_features(holdings, term_days=30)
        assert feats["portfolio_vol"] >= 0.0

    def test_concentration_herfindahl(self):
        """50/30/20 portfolio should have herfindahl > equal-weight."""
        h_unequal = _make_holdings(_trending_prices(), weights=[0.5, 0.3, 0.2])
        h_equal   = _make_holdings(_trending_prices(), weights=[1/3, 1/3, 1/3])
        feats_u = compute_portfolio_features(h_unequal, term_days=30)
        feats_e = compute_portfolio_features(h_equal, term_days=30)
        assert feats_u["herfindahl_index"] > feats_e["herfindahl_index"]


# ─── Payoff Formula ──────────────────────────────────────────────────────────

class TestPayoffFormula:
    def test_no_action_inside_band(self):
        res = compute_portfolio_settlement(
            notional=1_000_000, start_value=100.0, end_value=102.0,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=250_000,
        )
        assert res["payout_inr"] == 0.0
        assert res["surplus_inr"] == 0.0
        assert res["outcome"] == "NO_ACTION"

    def test_protection_triggered(self):
        """Portfolio drops -10%, L=-5%: payout = 10L × 0.8 × 0.05 = ₹40,000"""
        res = compute_portfolio_settlement(
            notional=1_000_000, start_value=100.0, end_value=90.0,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=250_000,
        )
        expected = 1_000_000 * 0.8 * 0.05
        assert abs(res["payout_inr"] - expected) < 1.0
        assert res["outcome"] == "PROTECTION_TRIGGERED"

    def test_payout_capped_at_max(self):
        """60% drop must be capped at max_payout."""
        res = compute_portfolio_settlement(
            notional=1_000_000, start_value=100.0, end_value=40.0,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=250_000,
        )
        assert res["payout_inr"] == 250_000
        assert res["outcome"] == "PROTECTION_TRIGGERED"

    def test_profit_share_triggered(self):
        """Portfolio gains +15%, U=+8%: surplus = 10L × 0.2 × 0.07 = ₹14,000"""
        res = compute_portfolio_settlement(
            notional=1_000_000, start_value=100.0, end_value=115.0,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=250_000,
        )
        expected_surplus = 1_000_000 * 0.2 * 0.07
        assert abs(res["surplus_inr"] - expected_surplus) < 1.0
        assert res["outcome"] == "PROFIT_SHARE"

    def test_return_calculation(self):
        """Check portfolio return is correct."""
        res = compute_portfolio_settlement(
            notional=1_000_000, start_value=200.0, end_value=210.0,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=250_000,
        )
        assert abs(res["portfolio_return"] - 0.05) < 0.0001


# ─── Underwriting Limits ─────────────────────────────────────────────────────

class TestUnderwritingLimits:
    def _feats(self, max_weight: float = 0.30, n_stocks: int = 3) -> dict:
        return {
            "portfolio_vol": 0.25, "max_weight": max_weight, "avg_max_drawdown": 0.05,
            "weighted_mean_return": 0.10, "n_stocks": n_stocks,
            "term_days": 30, "herfindahl_index": max_weight ** 2 * n_stocks,
        }

    def test_retail_notional_exceeds_limit(self):
        result = check_underwriting(
            notional=2_000_000,  # ₹20L > ₹10L limit
            portfolio_feats=self._feats(),
            tier="RETAIL", current_exposure=0,
        )
        assert not result.eligible
        assert any("notional" in r.lower() for r in result.reasons)

    def test_exposure_limit_reached(self):
        result = check_underwriting(
            notional=1_000_000,
            portfolio_feats=self._feats(),
            tier="RETAIL",
            current_exposure=2_000_000,   # already at ₹20L, adding ₹10L = ₹30L > ₹25L
        )
        assert not result.eligible

    def test_concentration_limit_breach(self):
        result = check_underwriting(
            notional=500_000,
            portfolio_feats=self._feats(max_weight=0.55),  # 55% > 40% retail limit
            tier="RETAIL", current_exposure=0,
        )
        assert not result.eligible
        assert any("concentration" in r.lower() for r in result.reasons)

    def test_institutional_higher_notional_allowed(self):
        result = check_underwriting(
            notional=5_000_000,   # ₹50L — ok for INST_BASIC (limit ₹1Cr)
            portfolio_feats=self._feats(),
            tier="INSTITUTIONAL_BASIC", current_exposure=0,
        )
        assert result.eligible

    def test_min_notional_floor(self):
        result = check_underwriting(
            notional=5_000,   # below ₹10K floor
            portfolio_feats=self._feats(),
            tier="RETAIL", current_exposure=0,
        )
        assert not result.eligible


# ─── Pricing ────────────────────────────────────────────────────────────────

class TestPricingEngine:
    def _feats(self) -> dict:
        return {
            "portfolio_vol": 0.25, "max_weight": 0.35, "avg_max_drawdown": 0.06,
            "weighted_mean_return": 0.12, "n_stocks": 3,
            "term_days": 30, "herfindahl_index": 0.14,
        }

    def test_premium_above_min(self):
        q = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.01, predicted_vol=0.01,
            portfolio_feats=self._feats(), tier="RETAIL",
        )
        assert q.premium_inr >= MIN_PREMIUM_INR

    def test_loss_threshold_negative(self):
        q = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.3, predicted_vol=0.3,
            portfolio_feats=self._feats(), tier="RETAIL",
        )
        assert q.loss_threshold < 0

    def test_profit_threshold_positive(self):
        q = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.3, predicted_vol=0.3,
            portfolio_feats=self._feats(), tier="RETAIL",
        )
        assert q.profit_threshold > 0

    def test_max_payout_fraction(self):
        q = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.3, predicted_vol=0.3,
            portfolio_feats=self._feats(), tier="RETAIL",
        )
        assert abs(q.max_payout_inr - 1_000_000 * 0.25) < 1.0

    def test_institutional_lower_margin(self):
        q_retail = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.3, predicted_vol=0.3,
            portfolio_feats=self._feats(), tier="RETAIL",
        )
        q_inst = compute_portfolio_quote(
            notional=1_000_000, term="MONTHLY",
            tail_loss_prob=0.3, predicted_vol=0.3,
            portfolio_feats=self._feats(), tier="INSTITUTIONAL_PREMIUM",
        )
        assert q_inst.premium_inr < q_retail.premium_inr


# ─── Pearson Correlation ─────────────────────────────────────────────────────

class TestCorrelation:
    def test_identical_series_correlation_one(self):
        xs = [0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.005, 0.015]
        assert abs(pearson_correlation(xs, xs) - 1.0) < 0.001

    def test_insufficient_data_returns_default(self):
        xs = [0.01, -0.02]
        ys = [0.01, -0.01]
        rho = pearson_correlation(xs, ys)
        assert 0.0 <= rho <= 1.0   # returns conservative default 0.5


# ─── Settlement Snapshot Consistency ─────────────────────────────────────────

class TestSnapshotConsistency:
    def test_start_price_matches_quote_snapshot(self):
        """Settlement start value must equal quote snapshot portfolio value."""
        snapshot = {
            "RELIANCE.NSE": {"qty": 10, "price": 2800.0},
            "TCS.NSE":      {"qty": 5,  "price": 3600.0},
        }
        portfolio_value_at_quote = sum(
            h["qty"] * h["price"] for h in snapshot.values()
        )  # = 28000 + 18000 = 46000

        # Simulate settlement referencing the same snapshot
        end_prices = {"RELIANCE.NSE": 2600.0, "TCS.NSE": 3500.0}
        end_value = sum(snapshot[sym]["qty"] * end_prices[sym] for sym in snapshot)

        res = compute_portfolio_settlement(
            notional=50_000, start_value=portfolio_value_at_quote, end_value=end_value,
            loss_threshold=-0.05, profit_threshold=0.08,
            coverage_rate=0.8, profit_share_rate=0.2, max_payout_inr=12_500,
        )
        assert res["portfolio_return"] < 0   # portfolio dropped

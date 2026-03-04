"""
pricing.py — Tier-aware INR premium pricing engine and underwriting rules.

Premium formula:
    premium = expected_payout + risk_margin + capital_fee

Tier-based margins and limits are configurable via a RulesConfig dict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Default tier configuration (fallback when /rules DB record is missing)
# ---------------------------------------------------------------------------

TERM_DAYS: Dict[str, int] = {
    "INTRADAY": 1,
    "WEEKLY":   7,
    "MONTHLY":  30,
}

DEFAULT_RULES: Dict[str, dict] = {
    "RETAIL": {
        "max_notional_per_policy": 1_000_000,       # ₹10 L
        "max_open_exposure":       2_500_000,        # ₹25 L
        "concentration_limit":     0.80,             # 80% max single stock
        "margin_pct":              0.30,             # risk margin on top of expected payout
        "min_premium_inr":         500,
        "max_payout_pct":          0.25,             # max_payout = notional × this
        "coverage_rate":           0.80,
        "profit_share_rate":       0.20,
    },
    "INSTITUTIONAL_BASIC": {
        "max_notional_per_policy": 10_000_000,
        "max_open_exposure":       50_000_000,
        "concentration_limit":     0.85,
        "margin_pct":              0.20,
        "min_premium_inr":         500,
        "max_payout_pct":          0.25,
        "coverage_rate":           0.80,
        "profit_share_rate":       0.15,
    },
    "INSTITUTIONAL_PREMIUM": {
        "max_notional_per_policy": 50_000_000,
        "max_open_exposure":       250_000_000,
        "concentration_limit":     0.90,
        "margin_pct":              0.15,
        "min_premium_inr":         500,
        "max_payout_pct":          0.25,
        "coverage_rate":           0.80,
        "profit_share_rate":       0.10,
    },
}

MIN_PREMIUM_INR = 500.0   # absolute floor


# ---------------------------------------------------------------------------
# Underwriting result
# ---------------------------------------------------------------------------

@dataclass
class UnderwritingResult:
    eligible:         bool
    reasons:          list[str] = field(default_factory=list)
    notional_used:    float = 0.0


@dataclass
class QuoteResult:
    premium_inr:      float
    loss_threshold:   float   # L  (negative, e.g. -0.03)
    profit_threshold: float   # U  (positive, e.g. +0.05)
    coverage_rate:    float   # c
    profit_share_rate: float  # s
    max_payout_inr:   float

    expected_payout:  float
    risk_margin:      float
    capital_fee:      float

    eligibility:      UnderwritingResult

    # ML outputs stored for audit
    tail_loss_prob:  float
    predicted_vol:   float


# ---------------------------------------------------------------------------
# Underwriting rules check
# ---------------------------------------------------------------------------

def check_underwriting(
    notional:          float,
    portfolio_feats:   dict,
    tier:              str,
    current_exposure:  float,   # sum of existing ACTIVE+MATURED policy notionals
    rules:             Optional[dict] = None,
) -> UnderwritingResult:
    """
    Enforce underwriting constraints and return eligibility decision.

    Args:
        notional:         requested insured notional (INR)
        portfolio_feats:  dict from compute_portfolio_features()
        tier:             'RETAIL' | 'INSTITUTIONAL_BASIC' | 'INSTITUTIONAL_PREMIUM'
        current_exposure: total currently hedged notional for the user/org
        rules:            override dict (from DB rules_config); falls back to DEFAULT_RULES

    Returns:
        UnderwritingResult
    """
    r        = (rules or DEFAULT_RULES).get(tier, DEFAULT_RULES["RETAIL"])
    reasons  = []

    # 1. Max notional per policy
    if notional > r["max_notional_per_policy"]:
        reasons.append(
            f"Requested notional ₹{notional:,.0f} exceeds tier limit "
            f"₹{r['max_notional_per_policy']:,.0f} for {tier}."
        )

    # 2. Max open exposure
    if current_exposure + notional > r["max_open_exposure"]:
        reasons.append(
            f"Adding this policy would take total exposure to "
            f"₹{current_exposure + notional:,.0f}, exceeding limit ₹{r['max_open_exposure']:,.0f}."
        )

    # 3. Concentration limit
    max_weight = portfolio_feats.get("max_weight", 0.0)
    if max_weight > r["concentration_limit"]:
        reasons.append(
            f"Portfolio concentration: largest holding weight {max_weight:.1%} exceeds "
            f"limit {r['concentration_limit']:.0%} for {tier}."
        )

    # 4. Minimum notional (₹10K floor)
    if notional < 10_000:
        reasons.append("Minimum insured notional is ₹10,000.")

    eligible = len(reasons) == 0
    return UnderwritingResult(eligible=eligible, reasons=reasons, notional_used=notional)


# ---------------------------------------------------------------------------
# Premium computation
# ---------------------------------------------------------------------------

def compute_portfolio_quote(
    notional:         float,
    term:             str,              # 'INTRADAY' | 'WEEKLY' | 'MONTHLY'
    tail_loss_prob:   float,
    predicted_vol:    float,
    portfolio_feats:  dict,
    tier:             str,
    current_exposure: float = 0.0,
    rules:            Optional[dict] = None,
) -> QuoteResult:
    """
    Compute premium and underwriting decision for a portfolio insurance policy.
    """
    r        = (rules or DEFAULT_RULES).get(tier, DEFAULT_RULES["RETAIL"])
    term_days = TERM_DAYS.get(term, 30)
    c        = r["coverage_rate"]
    s        = r["profit_share_rate"]
    margin   = r["margin_pct"]

    # Thresholds: volatility-scaled by term
    scale         = math.sqrt(term_days / 252)
    loss_threshold   = round(-1.0 * predicted_vol * scale, 4)      # L < 0
    profit_threshold = round(+1.5 * predicted_vol * scale, 4)      # U > 0

    # Average excess loss given tail event (conservative 1σ estimate)
    avg_excess_loss = predicted_vol * scale * 0.5

    # Premium components
    expected_payout = notional * c * tail_loss_prob * avg_excess_loss
    risk_margin     = expected_payout * margin
    capital_fee     = notional * 0.0003 * (term_days / 30)
    raw_premium     = expected_payout + risk_margin + capital_fee
    premium         = max(raw_premium, float(r["min_premium_inr"]))

    max_payout = notional * r["max_payout_pct"]

    # Underwriting check
    eligibility = check_underwriting(
        notional=notional,
        portfolio_feats=portfolio_feats,
        tier=tier,
        current_exposure=current_exposure,
        rules=rules,
    )

    return QuoteResult(
        premium_inr=round(premium, 2),
        loss_threshold=loss_threshold,
        profit_threshold=profit_threshold,
        coverage_rate=c,
        profit_share_rate=s,
        max_payout_inr=round(max_payout, 2),
        expected_payout=round(expected_payout, 2),
        risk_margin=round(risk_margin, 2),
        capital_fee=round(capital_fee, 2),
        eligibility=eligibility,
        tail_loss_prob=tail_loss_prob,
        predicted_vol=predicted_vol,
    )


# ---------------------------------------------------------------------------
# Settlement payoff
# ---------------------------------------------------------------------------

def compute_portfolio_settlement(
    notional:         float,
    start_value:      float,
    end_value:        float,
    loss_threshold:   float,    # L (negative)
    profit_threshold: float,    # U (positive)
    coverage_rate:    float,
    profit_share_rate: float,
    max_payout_inr:   float,
) -> dict:
    """
    Compute settlement payout from portfolio return.

    Returns dict with: portfolio_return, payout_inr, surplus_inr, outcome
    """
    if start_value <= 0:
        return {"portfolio_return": 0.0, "payout_inr": 0.0, "surplus_inr": 0.0, "outcome": "ERROR"}

    rp = (end_value - start_value) / start_value

    if rp < loss_threshold:
        excess_loss = abs(rp) - abs(loss_threshold)
        payout      = min(notional * coverage_rate * excess_loss, max_payout_inr)
        return {
            "portfolio_return": round(rp, 6),
            "payout_inr":       round(payout, 2),
            "surplus_inr":      0.0,
            "outcome":          "PROTECTION_TRIGGERED",
        }

    elif rp > profit_threshold:
        excess_return = rp - profit_threshold
        surplus       = notional * profit_share_rate * excess_return
        return {
            "portfolio_return": round(rp, 6),
            "payout_inr":       0.0,
            "surplus_inr":      round(surplus, 2),
            "outcome":          "PROFIT_SHARE",
        }

    return {
        "portfolio_return": round(rp, 6),
        "payout_inr":       0.0,
        "surplus_inr":      0.0,
        "outcome":          "NO_ACTION",
    }

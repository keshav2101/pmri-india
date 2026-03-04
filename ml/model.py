"""
model.py — XGBoost portfolio risk model for NSE/BSE cash equities.

Predicts tail-loss probability (probability of portfolio losing > 5% over term).
Falls back to a heuristic vol-based model if XGBoost is not available.
Model version is a SHA-256 hash of training feature names for reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np

from features import compute_portfolio_features

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "portfolio_vol", "max_weight", "avg_max_drawdown",
    "weighted_mean_return", "n_stocks", "term_days", "herfindahl_index",
]

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False
    logger.warning("XGBoost not available — using heuristic fallback model.")

# ─── Singleton ───────────────────────────────────────────────────────────────

_model: Optional[Any] = None
_model_version: str   = "heuristic-v1"


def _compute_version() -> str:
    digest = hashlib.sha256(json.dumps(FEATURE_NAMES, sort_keys=True).encode()).hexdigest()[:12]
    return f"xgb-v1-{digest}"


def _feature_vector(portfolio_feats: dict) -> list[float]:
    return [portfolio_feats.get(f, 0.0) for f in FEATURE_NAMES]


# ─── Heuristic fallback ──────────────────────────────────────────────────────

def _heuristic_tail_loss(portfolio_feats: dict) -> float:
    """
    Simple vol + drawdown heuristic when XGBoost is unavailable.
    Higher vol and concentration → higher tail-loss probability.
    """
    vol       = portfolio_feats.get("portfolio_vol", 0.25)
    drawdown  = portfolio_feats.get("avg_max_drawdown", 0.05)
    herf      = portfolio_feats.get("herfindahl_index", 0.25)
    term_days = portfolio_feats.get("term_days", 30)
    scale     = term_days / 252

    # Simplified: prob ≈ vol × sqrt(T) × concentration_penalty
    prob = min(0.95, vol * np.sqrt(scale) * (1 + drawdown + herf))
    return float(max(0.01, round(prob, 4)))


# ─── Train ───────────────────────────────────────────────────────────────────

def train(
    feature_rows: list[dict],
    labels: list[float],
    artifacts_dir: Optional[Path] = None,
) -> str:
    """Train XGBoost (or skip if unavailable). Return model version."""
    global _model, _model_version

    artifacts_dir = artifacts_dir or ARTIFACTS_DIR
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if not _XGB_AVAILABLE or len(feature_rows) < 50:
        logger.info("Using heuristic model (XGBoost not available or insufficient data).")
        _model_version = "heuristic-v1"
        meta = {"model_type": "heuristic", "version": _model_version, "n_samples": len(feature_rows)}
        (artifacts_dir / "model_meta.json").write_text(json.dumps(meta, indent=2))
        return _model_version

    X = np.array([[row.get(f, 0.0) for f in FEATURE_NAMES] for row in feature_rows])
    y = np.array(labels, dtype=float)

    clf = xgb.XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X, y)

    _model_version = _compute_version()
    _model = clf

    with open(artifacts_dir / "model.pkl", "wb") as f:
        pickle.dump(clf, f)

    meta = {
        "model_type": "xgboost",
        "version": _model_version,
        "feature_names": FEATURE_NAMES,
        "n_samples": len(feature_rows),
        "n_positive": int(sum(labels)),
    }
    (artifacts_dir / "model_meta.json").write_text(json.dumps(meta, indent=2))
    logger.info("Model trained: %s (n=%d)", _model_version, len(feature_rows))
    return _model_version


# ─── Load ────────────────────────────────────────────────────────────────────

def load_model(artifacts_dir: Optional[Path] = None) -> str:
    """Load persisted model from disk. Returns version string."""
    global _model, _model_version

    artifacts_dir = artifacts_dir or ARTIFACTS_DIR
    pkl_path  = artifacts_dir / "model.pkl"
    meta_path = artifacts_dir / "model_meta.json"

    if meta_path.exists():
        meta          = json.loads(meta_path.read_text())
        _model_version = meta.get("version", "heuristic-v1")
    else:
        _model_version = "heuristic-v1"

    if _XGB_AVAILABLE and pkl_path.exists():
        with open(pkl_path, "rb") as f:
            _model = pickle.load(f)
        logger.info("Loaded model: %s", _model_version)
    else:
        _model = None
        logger.info("Using heuristic model: %s", _model_version)

    return _model_version


# ─── Inference ───────────────────────────────────────────────────────────────

def predict_tail_loss(
    holdings: list[dict],   # [{"symbol": str, "weight": float, "prices": list[float]}]
    term_days: int = 30,
    artifacts_dir: Optional[Path] = None,
) -> dict:
    """
    Predict portfolio tail-loss probability.

    Returns dict with:
        tail_loss_prob, predicted_vol, portfolio_features, model_version
    """
    global _model, _model_version

    if _model is None and artifacts_dir:
        load_model(artifacts_dir)

    portfolio_feats = compute_portfolio_features(holdings, term_days=term_days)
    predicted_vol   = portfolio_feats["portfolio_vol"]

    if _model is not None and _XGB_AVAILABLE:
        X = np.array([_feature_vector(portfolio_feats)])
        tail_loss_prob = float(_model.predict_proba(X)[0][1])
    else:
        tail_loss_prob = _heuristic_tail_loss(portfolio_feats)

    return {
        "tail_loss_prob":    round(tail_loss_prob, 4),
        "predicted_vol":     round(predicted_vol, 4),
        "portfolio_features": portfolio_feats,
        "model_version":     _model_version,
    }

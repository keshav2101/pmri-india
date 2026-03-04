"""services/ml_service.py — ML service bridge for PMRI India."""
import sys
import os
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()

class MLService:
    def __init__(self):
        ml_path = str(Path(settings.ml_module_path).resolve())
        if ml_path not in sys.path:
            sys.path.insert(0, ml_path)

        self._model_module = None
        self._pricing_module = None

    def _ensure_loaded(self):
        if not self._model_module:
            import model
            import pricing
            self._model_module = model
            self._pricing_module = pricing
            # Load cached model
            self._model_module.load_model(Path(settings.model_artifacts_path))

    def predict_tail_loss(self, holdings: list, term_days: int) -> dict:
        self._ensure_loaded()
        return self._model_module.predict_tail_loss(
            holdings=holdings,
            term_days=term_days,
            artifacts_dir=Path(settings.model_artifacts_path)
        )

    def compute_quote(self, notional: float, term: str, prob: float, vol: float, feats: dict, tier: str, exposure: float, rules: dict = None):
        self._ensure_loaded()
        return self._pricing_module.compute_portfolio_quote(
            notional=notional, term=term, tail_loss_prob=prob, predicted_vol=vol,
            portfolio_feats=feats, tier=tier, current_exposure=exposure, rules=rules
        )
        
    def compute_settlement(self, notional: float, start_idx: float, end_idx: float, loss_threshold: float, profit_threshold: float, coverage_rate: float, profit_share_rate: float, max_payout: float):
        self._ensure_loaded()
        return self._pricing_module.compute_portfolio_settlement(
            notional, start_idx, end_idx, loss_threshold, profit_threshold, coverage_rate, profit_share_rate, max_payout
        )

ml_service = MLService()

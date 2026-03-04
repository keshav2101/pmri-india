"""
train.py — CLI training entry point for the ML model Docker container.

Usage:
    python train.py [--artifacts-dir /path/to/artifacts]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make ml/ importable
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Train PMRI India portfolio risk model")
    parser.add_argument("--artifacts-dir", default="./artifacts", help="Directory to save model artifacts")
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    data_dir = Path(__file__).parent / "data"

    # Generate demo data if not present
    csv_files = list(data_dir.glob("*.NSE.csv"))
    if not csv_files:
        logger.info("No demo data found — generating…")
        from data.generate_demo_data import main as gen_data
        gen_data()
        csv_files = list(data_dir.glob("*.NSE.csv"))

    # Load price series for each ticker
    logger.info("Loading price data for %d tickers…", len(csv_files))
    import csv as csv_module
    prices_map: dict[str, list[float]] = {}
    symbols: list[str] = []

    for csv_path in sorted(csv_files):
        ticker = csv_path.stem.replace(".NSE", "")
        prices = []
        with open(csv_path, newline="") as f:
            for row in csv_module.DictReader(f):
                prices.append(float(row["close"]))
        prices_map[ticker] = prices
        symbols.append(ticker)
        logger.info("  %s: %d days", ticker, len(prices))

    # Build feature matrix
    from features import build_feature_matrix
    logger.info("Building feature matrix for all terms…")
    all_features, all_labels = [], []
    for term_days in [1, 7, 30]:
        feats, labels = build_feature_matrix(symbols, prices_map, term_days=term_days)
        all_features.extend(feats)
        all_labels.extend(labels)
        logger.info("  term=%dd: %d samples (%.1f%% positive)", term_days, len(feats), 100 * sum(labels) / max(1, len(labels)))

    # Train
    from model import train as train_model
    version = train_model(all_features, all_labels, artifacts_dir=artifacts_dir)
    logger.info("Training complete. Model version: %s", version)
    logger.info("Artifacts saved to: %s", artifacts_dir)


if __name__ == "__main__":
    main()

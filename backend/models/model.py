# backend/models/model.py
"""
Quantara Walk-Forward Training + Backtest Export (Full Coverage)

This script:
1) Tries BOTH training window lengths: 126 and 252
2) Runs a CatBoost hyperparameter grid
3) Evaluates each config with WALK-FORWARD (rolling window) + 1-day gap
4) Picks best config using moderate+strong directional win rate (+ trade count tie-break)
5) Saves best final model artifacts
6) Writes:
   - backend/backtests/predictions_all.csv  (ALL OOS predictions)
   - backend/backtests/predictions.csv      (ONLY moderate+strong signals)

Notes:
- Backtest predictions are OUT-OF-SAMPLE (no leakage) due to the 1-day gap.
- Coverage per ticker ≈ N - (window + gap).
"""

from __future__ import annotations

import json
import joblib
import warnings
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

warnings.filterwarnings("ignore")

# Make sure this matches your actual filename on disk
from backend.models.model_preprocesser import load_model_data
from backend.models.evaluate import classify_confidence

# ----------------------------
# Config
# ----------------------------

GAP_DAYS = 1  # your requested 1-step gap to reduce leakage
WINDOW_CANDIDATES = [126, 252]  # try both
RETRAIN_EVERY = 5  # retrain every N predicted points to speed up walk-forward

RELAXED_THRESHOLDS: Dict[str, float] = {
    "do_not_trade_threshold": 0.5,
    "low_threshold": 0.75,
    "moderate_threshold": 1.5,
    "min_sigma_filter": 1.25,
}

HYPERPARAMETER_GRID: Dict[str, List[Any]] = {
    "depth": [5, 6, 7],
    "learning_rate": [0.03, 0.05],
    "l2_leaf_reg": [3, 5, 7],
    "iterations": [300, 500],
}

# Minimum trades so we don't “win” by firing almost no signals
MIN_TRADES_FOR_VALID = 50


@dataclass(frozen=True)
class Config:
    window: int
    depth: int
    learning_rate: float
    l2_leaf_reg: int
    iterations: int


# ----------------------------
# Metrics helpers
# ----------------------------

def _bucket_to_ui(bucket: str) -> str:
    if "strong" in bucket:
        return "strong"
    if "moderate" in bucket:
        return "moderate"
    if "low" in bucket:
        return "low"
    return "do_not_trade"


def compute_signal_metrics_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    rows contain per-prediction fields including:
    - y_true (actual model target)
    - mu_sigma (raw prediction)
    - raw_bucket
    - actual_return
    """
    if not rows:
        return {
            "strong_count": 0,
            "moderate_strong_count": 0,
            "strong_win_rate": None,
            "moderate_strong_win_rate": None,
            "strong_avg_return": None,
            "moderate_strong_avg_return": None,
        }

    df = pd.DataFrame(rows)

    strong_mask = df["raw_bucket"].isin(["strong_positive", "strong_negative"])
    mod_str_mask = df["raw_bucket"].isin(
        ["strong_positive", "strong_negative", "moderate_positive", "moderate_negative"]
    )

    out: Dict[str, Any] = {
        "strong_count": int(strong_mask.sum()),
        "moderate_strong_count": int(mod_str_mask.sum()),
        "strong_win_rate": None,
        "moderate_strong_win_rate": None,
        "strong_avg_return": None,
        "moderate_strong_avg_return": None,
    }

    # directional correctness based on SIGN(pred) == SIGN(y_true)
    # (y_true is your training target; actual_return is the realized pct change)
    if out["strong_count"] > 0:
        correct = np.sign(df.loc[strong_mask, "mu_sigma"].values) == np.sign(df.loc[strong_mask, "y_true"].values)
        out["strong_win_rate"] = float(np.mean(correct) * 100.0)
        out["strong_avg_return"] = float(np.mean(df.loc[strong_mask, "actual_return"].values) * 100.0)

    if out["moderate_strong_count"] > 0:
        correct = np.sign(df.loc[mod_str_mask, "mu_sigma"].values) == np.sign(df.loc[mod_str_mask, "y_true"].values)
        out["moderate_strong_win_rate"] = float(np.mean(correct) * 100.0)
        out["moderate_strong_avg_return"] = float(np.mean(df.loc[mod_str_mask, "actual_return"].values) * 100.0)

    return out


# ----------------------------
# Walk-forward engine (rolling window + gap)
# ----------------------------

def walk_forward_predict(
    X: np.ndarray,
    y: np.ndarray,
    y_pct: np.ndarray,
    dates: np.ndarray,
    tickers: np.ndarray,
    cfg: Config,
    thresholds: Dict[str, float],
    retrain_every: int = RETRAIN_EVERY,
    gap_days: int = GAP_DAYS,
) -> List[Dict[str, Any]]:
    """
    Generates OUT-OF-SAMPLE predictions across almost entire dataset.

    Rolling-window training:
      train window = [i - window - gap, i - gap)
      predict point = i

    retrain_every: train once, then reuse model for next retrain_every predictions.
    sigma is computed from training residuals for the current trained model.
    """

    rows: List[Dict[str, Any]] = []

    # group by ticker for proper chronological leakage control
    # (we need per-ticker time series ordering)
    df_meta = pd.DataFrame({
        "idx": np.arange(len(X)),
        "ticker": tickers,
        "date": pd.to_datetime(dates),
    }).sort_values(["ticker", "date"])

    # iterate each ticker separately
    for ticker, g in df_meta.groupby("ticker", sort=False):
        idxs = g["idx"].to_numpy()
        n = len(idxs)

        start_i = cfg.window + gap_days
        if n <= start_i:
            continue

        model = None
        sigma = None

        i = start_i
        while i < n:
            train_end = i - gap_days
            train_start = train_end - cfg.window
            train_slice = idxs[train_start:train_end]
            test_slice = idxs[i:min(i + retrain_every, n)]

            X_train = X[train_slice]
            y_train = y[train_slice]

            # train new model
            model = CatBoostRegressor(
                depth=cfg.depth,
                learning_rate=cfg.learning_rate,
                l2_leaf_reg=cfg.l2_leaf_reg,
                iterations=cfg.iterations,
                loss_function="RMSE",
                verbose=False,
                random_seed=42,
            )
            model.fit(X_train, y_train)

            # sigma from train residuals (stable + no look-ahead)
            train_pred = model.predict(X_train)
            sigma = float(np.std(y_train - train_pred))
            if sigma <= 0:
                sigma = 1e-9  # avoid division by zero

            # predict next block
            X_test = X[test_slice]
            pred_block = model.predict(X_test).astype(float)

            for j, global_idx in enumerate(test_slice):
                mu_sigma = float(pred_block[j])
                raw_bucket = classify_confidence(mu_sigma, sigma, **thresholds)
                ui_bucket = _bucket_to_ui(raw_bucket)

                direction = 1 if mu_sigma > 0 else -1

                rows.append({
                    "date": str(pd.to_datetime(dates[global_idx]).date()),
                    "ticker": str(tickers[global_idx]),
                    "prediction": direction,
                    "confidence_bucket": ui_bucket,       # strong/moderate/low/do_not_trade
                    "raw_bucket": raw_bucket,             # strong_positive, etc
                    "mu_sigma": mu_sigma,                 # raw model output
                    "actual_return": float(y_pct[global_idx]),
                    "y_true": float(y[global_idx]),       # for directional accuracy on target
                    "window": int(cfg.window),
                })

            i += retrain_every

    return rows


# ----------------------------
# Training final model + exports
# ----------------------------

def save_artifacts(
    project_root: Path,
    model: CatBoostRegressor,
    scaler: Any,
    ticker_encoder: Any,
    feature_schema: Dict[str, Any],
    metadata: Dict[str, Any],
) -> None:
    artifact_dir = project_root / "backend" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, artifact_dir / "catboost_model.joblib")
    joblib.dump(scaler, artifact_dir / "scaler.joblib")
    joblib.dump(ticker_encoder, artifact_dir / "ticker_encoder.joblib")

    with open(artifact_dir / "feature_schema.json", "w", encoding="utf-8") as f:
        json.dump(feature_schema, f, indent=2)

    with open(artifact_dir / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def export_predictions_csvs(project_root: Path, rows: List[Dict[str, Any]]) -> Tuple[Path, Path]:
    """
    Writes:
    - predictions_all.csv: all walk-forward predictions
    - predictions.csv: only moderate+strong (what your backtest panel uses)
    """
    out_dir = project_root / "backend" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)

    df_all = pd.DataFrame(rows).copy()

    # Keep columns your dashboard expects (and keep extras for debugging)
    keep_cols = [
        "date", "ticker", "prediction",
        "confidence_bucket", "raw_bucket",
        "mu_sigma", "actual_return",
        "window",
    ]
    df_all = df_all[keep_cols].sort_values(["ticker", "date"])

    all_path = out_dir / "predictions_all.csv"
    df_all.to_csv(all_path, index=False)

    # Trades-only file for your backtest logic
    trades_mask = df_all["raw_bucket"].isin([
        "moderate_positive", "moderate_negative",
        "strong_positive", "strong_negative",
    ])
    df_trades = df_all.loc[trades_mask].copy()

    trades_path = out_dir / "predictions.csv"
    df_trades.to_csv(trades_path, index=False)

    return all_path, trades_path


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    # Load data
    X, y, scaler, ticker_encoder, meta, feature_schema = load_model_data(
        return_meta=True,
        return_schema=True,
    )

    X = np.asarray(X)
    y = np.asarray(y, dtype=float)
    y_pct = np.asarray(meta["target_pct_change"], dtype=float)
    dates = np.asarray(meta["dates"])
    tickers = np.asarray(meta["tickers"])

    # Search over both window sizes + hyperparams
    results: List[Dict[str, Any]] = []

    for window in WINDOW_CANDIDATES:
        for depth, lr, l2, iters in product(
            HYPERPARAMETER_GRID["depth"],
            HYPERPARAMETER_GRID["learning_rate"],
            HYPERPARAMETER_GRID["l2_leaf_reg"],
            HYPERPARAMETER_GRID["iterations"],
        ):
            cfg = Config(window=window, depth=depth, learning_rate=lr, l2_leaf_reg=l2, iterations=iters)

            rows = walk_forward_predict(
                X=X,
                y=y,
                y_pct=y_pct,
                dates=dates,
                tickers=tickers,
                cfg=cfg,
                thresholds=RELAXED_THRESHOLDS,
                retrain_every=RETRAIN_EVERY,
                gap_days=GAP_DAYS,
            )

            # compute signal metrics on trades only
            trade_rows = [r for r in rows if r["raw_bucket"] in {
                "moderate_positive", "moderate_negative",
                "strong_positive", "strong_negative",
            }]

            metrics = compute_signal_metrics_from_rows(trade_rows)

            rec = {
                "window": window,
                "depth": depth,
                "learning_rate": lr,
                "l2_leaf_reg": l2,
                "iterations": iters,
                **metrics,
                "total_oos_points": len(rows),
                "total_trades": len(trade_rows),
            }

            # Basic validity filter: don't allow configs that trade almost never
            if rec["total_trades"] < MIN_TRADES_FOR_VALID:
                rec["valid"] = False
            else:
                rec["valid"] = True

            results.append(rec)

            print(
                f"[window={window}] depth={depth} lr={lr} l2={l2} iters={iters} | "
                f"trades={rec['total_trades']} | "
                f"mod+strong WR={rec['moderate_strong_win_rate']}"
            )

    df_results = pd.DataFrame(results)
    valid = df_results[df_results["valid"] == True].copy()
    if valid.empty:
        # Fall back to the best even if trade count is low
        valid = df_results.copy()

    # Choose best by:
    # 1) highest moderate+strong win rate
    # 2) tie-break: more strong_count
    # 3) tie-break: more total_trades
    valid = valid.sort_values(
        by=["moderate_strong_win_rate", "strong_count", "total_trades"],
        ascending=[False, False, False],
        na_position="last",
    )

    best_row = valid.iloc[0].to_dict()

    best_cfg = Config(
        window=int(best_row["window"]),
        depth=int(best_row["depth"]),
        learning_rate=float(best_row["learning_rate"]),
        l2_leaf_reg=int(best_row["l2_leaf_reg"]),
        iterations=int(best_row["iterations"]),
    )

    print("\n✅ BEST CONFIG SELECTED:")
    print(best_cfg)
    print(f"Trades: {int(best_row.get('total_trades', 0))}")
    print(f"Moderate+Strong Win Rate: {best_row.get('moderate_strong_win_rate')}")

    # Generate final walk-forward predictions for BEST config
    best_rows_all = walk_forward_predict(
        X=X,
        y=y,
        y_pct=y_pct,
        dates=dates,
        tickers=tickers,
        cfg=best_cfg,
        thresholds=RELAXED_THRESHOLDS,
        retrain_every=RETRAIN_EVERY,
        gap_days=GAP_DAYS,
    )

    all_path, trades_path = export_predictions_csvs(project_root, best_rows_all)
    print(f"\n🧾 Wrote full OOS predictions: {all_path}")
    print(f"🧾 Wrote trades-only predictions: {trades_path}")

    # Train final production model on ALL data (best hyperparams)
    # (This is what you'll use for live inference; backtest is still walk-forward)
    final_model = CatBoostRegressor(
        depth=best_cfg.depth,
        learning_rate=best_cfg.learning_rate,
        l2_leaf_reg=best_cfg.l2_leaf_reg,
        iterations=best_cfg.iterations,
        loss_function="RMSE",
        verbose=False,
        random_seed=42,
    )
    final_model.fit(X, y)

    metadata = {
        "training_timestamp": datetime.utcnow().isoformat(),
        "selection_method": "walk_forward_rolling_window_with_gap",
        "gap_days": GAP_DAYS,
        "retrain_every": RETRAIN_EVERY,
        "window_candidates": WINDOW_CANDIDATES,
        "best_config": {
            "window": best_cfg.window,
            "depth": best_cfg.depth,
            "learning_rate": best_cfg.learning_rate,
            "l2_leaf_reg": best_cfg.l2_leaf_reg,
            "iterations": best_cfg.iterations,
        },
        "best_metrics": {
            "strong_count": int(best_row.get("strong_count", 0)),
            "moderate_strong_count": int(best_row.get("moderate_strong_count", 0)),
            "strong_win_rate": best_row.get("strong_win_rate"),
            "moderate_strong_win_rate": best_row.get("moderate_strong_win_rate"),
            "strong_avg_return": best_row.get("strong_avg_return"),
            "moderate_strong_avg_return": best_row.get("moderate_strong_avg_return"),
            "total_oos_points": int(best_row.get("total_oos_points", 0)),
            "total_trades": int(best_row.get("total_trades", 0)),
        },
    }

    save_artifacts(
        project_root=project_root,
        model=final_model,
        scaler=scaler,
        ticker_encoder=ticker_encoder,
        feature_schema=feature_schema,
        metadata=metadata,
    )

    print("\n✅ Training + walk-forward backtest export complete.")
    print("Next: point your backtest panel to backend/backtests/predictions.csv")


if __name__ == "__main__":
    main()

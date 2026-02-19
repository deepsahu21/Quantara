# backend/models/evaluate.py
"""
Quantara Model Evaluation & Backtest Export

Responsibilities:
1. Evaluate trained models (MAE, RMSE, R², signal diagnostics)
2. Define confidence bucketing logic (single source of truth)
3. Export prediction-level data for offline backtesting

This file does NOT:
- simulate trades
- compute equity curves
- apply holding strategies
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# -------------------------------------------------------------------
# Confidence Classification
# -------------------------------------------------------------------

def classify_confidence(
    prediction: float,
    sigma: float,
    do_not_trade_threshold: float = 0.5,  # kept for compatibility (not used directly below)
    low_threshold: float = 1.0,
    moderate_threshold: float = 2.0,
    min_sigma_filter: float = 1.25,
) -> str:
    """
    Classify prediction into confidence buckets based on |prediction| / sigma.

    Returns one of:
      - do_not_trade
      - low_positive / low_negative
      - moderate_positive / moderate_negative
      - strong_positive / strong_negative
    """
    if sigma is None or sigma <= 0:
        return "do_not_trade"

    strength = abs(prediction) / sigma

    # Hard floor: ignore ultra-weak signals entirely
    if strength < min_sigma_filter:
        return "do_not_trade"

    if strength < low_threshold:
        return "low_positive" if prediction > 0 else "low_negative"

    if strength < moderate_threshold:
        return "moderate_positive" if prediction > 0 else "moderate_negative"

    return "strong_positive" if prediction > 0 else "strong_negative"


# -------------------------------------------------------------------
# Model Evaluation (Training / Validation Time)
# -------------------------------------------------------------------

def evaluate_model(
    name: str,
    model: Any,
    X_train,
    y_train,
    X_test,
    y_test,
    y_test_pct_change=None,
    **confidence_kwargs,
) -> Dict[str, Any]:
    """
    Evaluate model quality and signal behavior.
    NOT used for backtesting.
    """
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    residuals = y_test - y_test_pred
    sigma = float(np.std(residuals)) if len(residuals) else 0.0

    metrics: Dict[str, Any] = {
        "name": name,
        "train_mae": float(mean_absolute_error(y_train, y_train_pred)),
        "test_mae": float(mean_absolute_error(y_test, y_test_pred)),
        "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
        "test_rmse": float(np.sqrt(mean_squared_error(y_test, y_test_pred))),
        "train_r2": float(r2_score(y_train, y_train_pred)),
        "test_r2": float(r2_score(y_test, y_test_pred)),
        "sigma": sigma,
    }

    buckets = np.array([classify_confidence(float(pred), sigma, **confidence_kwargs) for pred in y_test_pred])

    unique, counts = np.unique(buckets, return_counts=True)
    bucket_counts = {str(k): int(v) for k, v in zip(unique, counts)}
    total = int(len(buckets)) if len(buckets) else 1
    bucket_pcts = {k: float(v / total * 100) for k, v in bucket_counts.items()}

    metrics.update({"bucket_counts": bucket_counts, "bucket_pcts": bucket_pcts})
    return metrics


# -------------------------------------------------------------------
# Backtest Prediction Export
# -------------------------------------------------------------------

def export_predictions_for_backtest(
    model: Any,
    X,
    y_pct_change,
    dates,
    tickers,
    output_dir,
    confidence_kwargs: Dict[str, Any],
    sigma: Optional[float] = None,
) -> pd.DataFrame:
    """
    Export prediction-level data for offline backtesting.

    Writes ONLY Moderate + Strong signals.

    Output columns:
      date, ticker, prediction, confidence_bucket, raw_bucket, mu_sigma, actual_return
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    y_pred = np.asarray(model.predict(X), dtype=float)

    # Prefer sigma passed from training selection. Fallback if not provided.
    if sigma is None or sigma <= 0:
        sigma = float(np.std(y_pred - np.mean(y_pred))) if len(y_pred) else 0.0

    rows = []
    for i in range(len(y_pred)):
        mu_sigma = float(y_pred[i])
        raw_bucket = classify_confidence(mu_sigma, float(sigma), **confidence_kwargs)

        # Drop weak + do_not_trade signals at the data layer
        if raw_bucket not in {
            "moderate_positive",
            "moderate_negative",
            "strong_positive",
            "strong_negative",
        }:
            continue

        confidence_bucket = "strong" if "strong" in raw_bucket else "moderate"
        direction = 1 if mu_sigma > 0 else -1

        rows.append(
            {
                "date": dates[i],
                "ticker": tickers[i],
                "prediction": direction,
                "confidence_bucket": confidence_bucket,
                "raw_bucket": raw_bucket,
                "mu_sigma": mu_sigma,
                "actual_return": float(y_pct_change[i]),
            }
        )

    df = pd.DataFrame(rows)

    output_path = output_dir / "predictions.csv"

    # Append if exists (multi-stock support)
    if output_path.exists():
        df.to_csv(output_path, mode="a", header=False, index=False)
    else:
        df.to_csv(output_path, index=False)

    return df


# -------------------------------------------------------------------
# Real-Time Prediction (Dashboard Inference)
# -------------------------------------------------------------------

def predict_with_confidence(
    model: Any,
    X_input,
    sigma: float,
    rolling_vol: float,
    **confidence_kwargs,
) -> Dict[str, Any]:
    """
    Single-step prediction for dashboard inference.
    """
    mu_sigma = float(model.predict(X_input)[0])
    mu_pct = float(mu_sigma * rolling_vol)

    raw_bucket = classify_confidence(mu_sigma, sigma, **confidence_kwargs)

    if "strong" in raw_bucket:
        confidence = "Strong"
    elif "moderate" in raw_bucket:
        confidence = "Moderate"
    else:
        confidence = "Do Not Trade"

    return {
        "mu_sigma": mu_sigma,
        "mu_pct": mu_pct,
        "confidence": confidence,
        "direction": "positive" if mu_sigma > 0 else "negative",
        "confidence_bucket": raw_bucket,
        "expected_move_pct": abs(mu_pct),
    }

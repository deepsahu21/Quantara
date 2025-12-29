"""
CatBoost Fine-Tuning Script for Quantara
Focuses on signal quality metrics, not RMSE

Outputs (artifacts) -> backend/artifacts/
- catboost_model.joblib
- scaler.joblib
- ticker_encoder.joblib
- feature_schema.json
- model_metadata.json
"""

import os
import json
import joblib
import warnings
import numpy as np
from datetime import datetime
from itertools import product
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor

warnings.filterwarnings("ignore")

from backend.models.model_preprocessor import load_model_data
from backend.models.evaluate import classify_confidence


# ============================================================
# Config
# ============================================================

RELAXED_THRESHOLDS = {
    "do_not_trade_threshold": 0.5,
    "low_threshold": 0.75,
    "moderate_threshold": 1.5,
    "min_sigma_filter": 1.25,
}

HYPERPARAMETER_GRID = {
    "depth": [5, 6, 7],
    "learning_rate": [0.03, 0.05],
    "l2_leaf_reg": [3, 5, 7],
    "iterations": [300, 500],
}


# ============================================================
# Metrics
# ============================================================

def calculate_signal_metrics(y_test, y_pred, y_test_pct_change, sigma, thresholds):
    confidence_buckets = np.array([
        classify_confidence(pred, sigma, **thresholds)
        for pred in y_pred
    ])

    strong_mask = np.isin(confidence_buckets, ["strong_positive", "strong_negative"])
    moderate_strong_mask = np.isin(
        confidence_buckets,
        ["strong_positive", "strong_negative", "moderate_positive", "moderate_negative"],
    )

    metrics = {
        "strong_count": int(np.sum(strong_mask)),
        "moderate_strong_count": int(np.sum(moderate_strong_mask)),
        "strong_win_rate": None,
        "moderate_strong_win_rate": None,
        "strong_avg_return": None,
        "moderate_strong_avg_return": None,
        "strong_negative_avg_return": None,
        "strong_positive_avg_return": None,
        "strong_downside_accuracy": None,
        "sigma": float(sigma),
    }

    if metrics["strong_count"] > 0:
        correct = np.sign(y_pred[strong_mask]) == np.sign(y_test[strong_mask])
        metrics["strong_win_rate"] = float(np.mean(correct) * 100)
        metrics["strong_avg_return"] = float(np.mean(y_test_pct_change[strong_mask]) * 100)

        neg_mask = strong_mask & (y_pred < 0)
        pos_mask = strong_mask & (y_pred > 0)

        if np.sum(neg_mask) > 0:
            metrics["strong_negative_avg_return"] = float(np.mean(y_test_pct_change[neg_mask]) * 100)
            metrics["strong_downside_accuracy"] = float(
                np.mean(np.sign(y_pred[neg_mask]) == np.sign(y_test[neg_mask])) * 100
            )

        if np.sum(pos_mask) > 0:
            metrics["strong_positive_avg_return"] = float(np.mean(y_test_pct_change[pos_mask]) * 100)

    if metrics["moderate_strong_count"] > 0:
        correct = np.sign(y_pred[moderate_strong_mask]) == np.sign(y_test[moderate_strong_mask])
        metrics["moderate_strong_win_rate"] = float(np.mean(correct) * 100)
        metrics["moderate_strong_avg_return"] = float(
            np.mean(y_test_pct_change[moderate_strong_mask]) * 100
        )

    return metrics


def evaluate_consensus(cat_model, lgbm_model, X_test, y_test, y_test_pct_change, thresholds):
    cat_pred = cat_model.predict(X_test)
    lgbm_pred = lgbm_model.predict(X_test)

    residuals = y_test - cat_pred
    sigma = np.std(residuals)

    consensus_mask = (np.sign(cat_pred) == np.sign(lgbm_pred)) & (cat_pred != 0)
    consensus_pred = np.where(consensus_mask, cat_pred, 0)

    metrics = calculate_signal_metrics(
        y_test=y_test,
        y_pred=consensus_pred,
        y_test_pct_change=y_test_pct_change,
        sigma=sigma,
        thresholds=thresholds,
    )

    metrics["consensus_agreement_rate"] = float(np.mean(consensus_mask) * 100)
    return metrics


# ============================================================
# Main
# ============================================================

def main():
    # --------------------------------------------------------
    # Load data (+ schema)
    # --------------------------------------------------------
    X, y, scaler, ticker_encoder, meta, feature_schema = load_model_data(
        return_meta=True,
        return_schema=True,
    )

    y_pct_change = meta["target_pct_change"]

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    y_test_pct_change = y_pct_change[split_idx:]

    print(f"Data loaded: {len(X_train)} train, {len(X_test)} test samples")
    print(f"Features: {X_train.shape[1]}\n")

    # --------------------------------------------------------
    # Grid search
    # --------------------------------------------------------
    param_combinations = list(product(
        HYPERPARAMETER_GRID["depth"],
        HYPERPARAMETER_GRID["learning_rate"],
        HYPERPARAMETER_GRID["l2_leaf_reg"],
        HYPERPARAMETER_GRID["iterations"],
    ))

    print(f"Testing {len(param_combinations)} parameter combinations...\n")

    all_results = []

    for depth, lr, l2, iters in param_combinations:
        model = CatBoostRegressor(
            depth=depth,
            learning_rate=lr,
            l2_leaf_reg=l2,
            iterations=iters,
            loss_function="RMSE",
            verbose=False,
            random_seed=42,
        )

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        sigma = np.std(y_test - y_pred)
        metrics = calculate_signal_metrics(
            y_test=y_test,
            y_pred=y_pred,
            y_test_pct_change=y_test_pct_change,
            sigma=sigma,
            thresholds=RELAXED_THRESHOLDS,
        )

        all_results.append({
            "depth": depth,
            "learning_rate": lr,
            "l2_leaf_reg": l2,
            "iterations": iters,
            **metrics,
        })

    valid = [r for r in all_results if r["moderate_strong_win_rate"] is not None]
    if not valid:
        raise RuntimeError("No valid models produced moderate/strong predictions. Check thresholds/data.")

    valid.sort(
        key=lambda r: (
            r["moderate_strong_win_rate"],
            r["strong_count"],
            r["strong_downside_accuracy"] or 0,
        ),
        reverse=True,
    )

    best_result = valid[0]
    print("\n✅ Best CatBoost Model Selected")
    print(best_result)

    # Retrain best model on train split (same as you did)
    best_model = CatBoostRegressor(
        depth=best_result["depth"],
        learning_rate=best_result["learning_rate"],
        l2_leaf_reg=best_result["l2_leaf_reg"],
        iterations=best_result["iterations"],
        loss_function="RMSE",
        verbose=False,
        random_seed=42,
    )
    best_model.fit(X_train, y_train)

    # --------------------------------------------------------
    # Consensus metrics (optional but useful)
    # --------------------------------------------------------
    lgbm_model = LGBMRegressor(
        n_estimators=100,
        learning_rate=0.01,
        num_leaves=31,
        random_state=42,
    )
    lgbm_model.fit(X_train, y_train)

    consensus_metrics = evaluate_consensus(
        cat_model=best_model,
        lgbm_model=lgbm_model,
        X_test=X_test,
        y_test=y_test,
        y_test_pct_change=y_test_pct_change,
        thresholds=RELAXED_THRESHOLDS,
    )

    print("\nConsensus Metrics:")
    for k, v in consensus_metrics.items():
        print(f"{k}: {v}")

    # --------------------------------------------------------
    # Save artifacts to backend/artifacts (ALWAYS)
    # --------------------------------------------------------
    project_root = os.path.abspath(os.path.join(__file__, "../../.."))  # -> Quantara/
    artifact_dir = os.path.join(project_root, "backend", "artifacts")
    os.makedirs(artifact_dir, exist_ok=True)

    # Save schema
    with open(os.path.join(artifact_dir, "feature_schema.json"), "w") as f:
        json.dump(feature_schema, f, indent=2)

    # Save model + preprocessors
    joblib.dump(best_model, os.path.join(artifact_dir, "catboost_model.joblib"))
    joblib.dump(scaler, os.path.join(artifact_dir, "scaler.joblib"))
    joblib.dump(ticker_encoder, os.path.join(artifact_dir, "ticker_encoder.joblib"))

    # Save metadata (IMPORTANT: include sigma!)
    metadata = {
        "model_type": "CatBoostRegressor",
        "training_timestamp": datetime.utcnow().isoformat(),
        "best_params": {
            "depth": best_result["depth"],
            "learning_rate": best_result["learning_rate"],
            "l2_leaf_reg": best_result["l2_leaf_reg"],
            "iterations": best_result["iterations"],
        },
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "feature_count": int(X_train.shape[1]),
        "feature_schema_path": "backend/artifacts/feature_schema.json",
        "signal_metrics": {
            # include sigma so inference can read it
            "sigma": float(best_result["sigma"]),
            "strong_count": int(best_result["strong_count"]),
            "moderate_strong_count": int(best_result["moderate_strong_count"]),
            "moderate_strong_win_rate": best_result["moderate_strong_win_rate"],
            "strong_win_rate": best_result.get("strong_win_rate"),
            "strong_downside_accuracy": best_result.get("strong_downside_accuracy"),
        },
        "consensus_metrics": consensus_metrics,
    }

    with open(os.path.join(artifact_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n💾 Artifacts saved to: {artifact_dir}")
    print("\n✅ Fine-tuning complete.")


if __name__ == "__main__":
    main()

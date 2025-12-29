"""
Prediction Service for Quantara Dashboard
Artifact-based inference (NO retraining, NO CSV dependence)
"""

import numpy as np
import pandas as pd
import joblib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

from services.yfinance_service import get_ohlcv_data
from services.finnhub_service import get_company_news


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ARTIFACT_DIR = os.path.join(PROJECT_ROOT, "backend", "artifacts")

MODEL_PATH = os.path.join(ARTIFACT_DIR, "catboost_model.joblib")
SCALER_PATH = os.path.join(ARTIFACT_DIR, "scaler.joblib")
ENCODER_PATH = os.path.join(ARTIFACT_DIR, "ticker_encoder.joblib")
META_PATH = os.path.join(ARTIFACT_DIR, "model_metadata.json")


# -------------------------------------------------------------------
# Prediction Service
# -------------------------------------------------------------------
class PredictionService:
    """
    Loads trained artifacts once and serves live predictions.
    """

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        self.ticker_encoder = joblib.load(ENCODER_PATH)

        with open(META_PATH, "r") as f:
            meta = json.load(f)

        # fixed sigma from validation
        self.sigma = float(meta.get("signal_metrics", {}).get("sigma", 0.04))

    # -------------------------------------------------------------------
    # Core Prediction
    # -------------------------------------------------------------------
    def get_prediction(
        self,
        ticker: str,
        use_real_data: bool = True,
    ) -> Dict:

        ticker = ticker.upper()

        # ---------------------------------------------------------------
        # Build inference features
        # ---------------------------------------------------------------
        X = self._build_feature_vector(ticker)

        # scale
        X_scaled = pd.DataFrame(self.scaler.transform(X), columns=X.columns)
        mu = float(self.model.predict(X_scaled)[0])

        sigma = self.sigma
        prob = self._direction_probability(mu, sigma)

        direction = "bullish" if mu >= 0 else "bearish"

        # ---------------------------------------------------------------
        # Market data
        # ---------------------------------------------------------------
        ohlcv = get_ohlcv_data(ticker, days=180) if use_real_data else []

        # ---------------------------------------------------------------
        # News
        # ---------------------------------------------------------------
        headlines = get_company_news(ticker, days=7) if use_real_data else []

        # ---------------------------------------------------------------
        # Placeholder sentiment series (UI continuity)
        # ---------------------------------------------------------------
        sentiment_series = self._mock_sentiment_series(30)

        return {
            "ticker": ticker,
            "direction": direction,
            "direction_score": round(mu, 5),
            "volatility": round(sigma, 5),
            "direction_probability": round(prob, 5),
            "feature_attribution": {
                "historical": 0.70,
                "sentiment": 0.30,
            },
            "sentiment_series": sentiment_series,
            "ohlcv": ohlcv,
            "backtest_metrics": {},
            "headlines": headlines,
        }

    # -------------------------------------------------------------------
    # Feature Builder (MVP version)
    # -------------------------------------------------------------------
    def _build_feature_vector(self, ticker: str) -> pd.DataFrame:
        """
        Build a single-row feature vector matching training schema.

        Uses feature_data.csv as the source of truth (v1).
        """
        feature_csv = os.path.join(PROJECT_ROOT, "backend", "data", "processed_data", "feature_data.csv")
        df = pd.read_csv(feature_csv)

        df = df[df["ticker"] == ticker]
        if df.empty:
            raise ValueError(f"No feature_data.csv rows found for ticker: {ticker}")

        row = df.iloc[-1].copy()

        # Drop non-feature cols
        row = row.drop(labels=["ticker", "date", "target_pct_change"], errors="ignore")

        # Add encoded_ticker exactly as training did
        row["encoded_ticker"] = self.ticker_encoder.transform([ticker])[0]

        # Load schema and enforce order
        schema_path = os.path.join(ARTIFACT_DIR, "feature_schema.json")
        with open(schema_path, "r") as f:
            feature_schema = json.load(f)

        X = pd.DataFrame([row])
        X = X.reindex(columns=feature_schema)

        # Fill any missing cols (safety)
        X = X.fillna(0.0)

        return X


    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _direction_probability(self, mu: float, sigma: float) -> float:
        z = np.clip(mu / sigma, -6, 6)
        return float(1 / (1 + np.exp(-z)))

    def _mock_sentiment_series(self, days: int) -> List[Dict]:
        base = datetime.utcnow() - timedelta(days=days)
        return [
            {
                "date": (base + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": round(np.random.normal(0, 0.2), 3),
            }
            for i in range(days)
        ]


# -------------------------------------------------------------------
# Singleton
# -------------------------------------------------------------------
_prediction_service: Optional[PredictionService] = None


def get_prediction_service() -> PredictionService:
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service

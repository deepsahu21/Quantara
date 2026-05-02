"""
Prediction service (backend/services/prediction_service.py)

Uses the trained CatBoost model (artifacts/catboost_model.joblib) for live inference.
Falls back to a volatility heuristic if artifacts are unavailable.

Returns the same response shape as before so app.py's _normalize_prediction_contract
and the frontend contract are unaffected.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from backend.services.yfinance_service import get_ohlcv_data
from backend.services.finnhub_service import get_company_news
from backend.models.evaluate import classify_confidence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Artifact loading (once at startup)
# ---------------------------------------------------------------------------
_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"

_MODEL = None
_SCALER = None
_TICKER_ENCODER = None
_FEATURE_SCHEMA: Optional[List[str]] = None


def _load_artifacts() -> bool:
    global _MODEL, _SCALER, _TICKER_ENCODER, _FEATURE_SCHEMA
    try:
        _MODEL = joblib.load(_ARTIFACTS_DIR / "catboost_model.joblib")
        _SCALER = joblib.load(_ARTIFACTS_DIR / "scaler.joblib")
        _TICKER_ENCODER = joblib.load(_ARTIFACTS_DIR / "ticker_encoder.joblib")
        with open(_ARTIFACTS_DIR / "feature_schema.json", encoding="utf-8") as f:
            _FEATURE_SCHEMA = json.load(f)
        logger.info("Model artifacts loaded from %s", _ARTIFACTS_DIR)
        return True
    except Exception as e:
        logger.warning("Could not load model artifacts: %s — using volatility fallback", e)
        return False


# ---------------------------------------------------------------------------
# Feature engineering for live inference
# ---------------------------------------------------------------------------

def _build_features(ticker: str, ohlcv: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """
    Engineer one inference row from OHLCV history using the same feature
    schema the model was trained on (feature_schema.json).

    Requires at least 16 rows (14 for rolling_vol + 1 lag + 1 current).
    Sentiment features default to 0 since FinBERT is not run at inference time.
    """
    if len(ohlcv) < 16:
        return None

    df = pd.DataFrame(ohlcv)[["date", "open", "high", "low", "close", "volume"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.rename(columns={
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
    })

    # Returns and rolling volatility
    df["daily_return"] = df["close_price"].pct_change()
    df["rolling_vol"] = df["daily_return"].rolling(14).std()

    # Lag-1 price/volume features
    for col in ["open_price", "high_price", "low_price", "close_price", "volume"]:
        df[f"{col}_lag1"] = df[col].shift(1)

    # Sentiment (not available at runtime — default to 0)
    for col in ["sentiment_score", "polarity", "headline_count",
                "sentiment_score_lag1", "polarity_lag1", "headline_count_lag1"]:
        df[col] = 0.0

    # Calendar features
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year

    # Ticker encoding — fall back to median class for unseen tickers
    try:
        encoded = int(_TICKER_ENCODER.transform([ticker.upper()])[0])
    except ValueError:
        encoded = len(_TICKER_ENCODER.classes_) // 2
    df["encoded_ticker"] = encoded

    row = df.dropna().iloc[-1:].copy()
    if row.empty:
        return None

    return row[_FEATURE_SCHEMA]


# ---------------------------------------------------------------------------
# Helpers shared by ML and fallback paths
# ---------------------------------------------------------------------------

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _confidence_from_vol(vol_pct: float) -> float:
    score = 1.0 - (vol_pct - 0.5) / (3.0 - 0.5)
    return _clip(score, 0.50, 0.99)


def _band(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.70:
        return "Moderate"
    return "Low"


def _normalize_headlines(raw: Any) -> List[Dict[str, Any]]:
    if not raw or not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "headline": item.get("headline") or item.get("title") or "",
                "title": item.get("title") or item.get("headline") or "",
                "url": item.get("url") or item.get("link") or "",
                "source": item.get("source") or item.get("publisher") or "",
                "datetime": item.get("datetime") or item.get("published_at") or "",
                "summary": item.get("summary") or item.get("description") or "",
            }
        )
    return [h for h in out if (h.get("headline") or h.get("title"))]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

@dataclass
class PredictionService:
    model_name: str = "catboost_walk_forward"

    def get_prediction(self, ticker: str, days: int = 21) -> Dict[str, Any]:
        t = ticker.upper().strip()
        # Fetch enough history for rolling_vol (14 days) + lag + some buffer
        ohlcv = get_ohlcv_data(t, days=252)

        if not isinstance(ohlcv, list) or len(ohlcv) < 20:
            return self._fallback_response(t, ohlcv or [])

        # ---- ML inference (uses trained CatBoost model) ----
        if _MODEL is not None and _SCALER is not None and _FEATURE_SCHEMA is not None:
            features = _build_features(t, ohlcv)
            if features is not None:
                try:
                    X_scaled = _SCALER.transform(features)
                    raw_pred = float(_MODEL.predict(X_scaled)[0])

                    # rolling_vol is in the same units as the prediction (pct change)
                    # and serves as the sigma proxy for confidence bucketing
                    rolling_vol = float(features["rolling_vol"].iloc[0])
                    sigma = rolling_vol if rolling_vol > 0 else 1e-4

                    raw_bucket = classify_confidence(
                        raw_pred, sigma,
                        do_not_trade_threshold=0.5,
                        low_threshold=0.75,
                        moderate_threshold=1.5,
                        min_sigma_filter=1.25,
                    )

                    direction = "up" if raw_pred > 0 else "down"
                    expected_move_pct = raw_pred * 100.0

                    if "strong" in raw_bucket:
                        band, score = "High", 0.90
                    elif "moderate" in raw_bucket:
                        band, score = "Moderate", 0.72
                    else:
                        band, score = "Low", 0.55

                    headlines = self._fetch_headlines(t)
                    return self._build_response(t, expected_move_pct, score, band, direction, headlines)

                except Exception as e:
                    logger.warning("ML inference failed for %s: %s — falling back to heuristic", t, e)

        return self._fallback_response(t, ohlcv)

    # ---- volatility heuristic fallback (unchanged logic) ----
    def _fallback_response(self, t: str, ohlcv: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not ohlcv or len(ohlcv) < 20:
            return self._build_response(t, 0.0, 0.50, "Low", "flat", [])

        closes = [float(row.get("close", 0.0)) for row in ohlcv if isinstance(row, dict)]
        rets: List[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            if prev != 0:
                rets.append((closes[i] - prev) / prev)

        window = rets[-60:] if len(rets) >= 60 else rets
        if not window:
            vol = 0.0
        else:
            mean = sum(window) / len(window)
            var = sum((x - mean) ** 2 for x in window) / max(1, len(window) - 1)
            vol = var ** 0.5

        vol_pct = abs(vol) * 100.0
        last_ret = rets[-1] if rets else 0.0
        direction = "up" if last_ret > 0 else ("down" if last_ret < 0 else "flat")
        expected_move_pct = -vol_pct if direction == "down" else (vol_pct if direction == "up" else 0.0)
        score = _confidence_from_vol(vol_pct)
        band = _band(score)

        headlines = self._fetch_headlines(t)
        return self._build_response(t, expected_move_pct, score, band, direction, headlines)

    def _fetch_headlines(self, t: str) -> List[Dict[str, Any]]:
        try:
            raw = get_company_news(t, days=7) or []
            return _normalize_headlines(raw)
        except Exception:
            return []

    def _build_response(
        self,
        t: str,
        expected_move_pct: float,
        score: float,
        band: str,
        direction: str,
        headlines: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        expected_move_pct = round(float(expected_move_pct), 4)
        score = round(float(score), 4)

        forecast = {
            "expected_move_pct": expected_move_pct,
            "confidence": band,
            "confidence_score": score,
            "expectedMovePct": expected_move_pct,
            "confidenceBand": band,
            "confidenceScore": score,
            "nextDayExpectedMovePct": expected_move_pct,
            "predictedMovePct": expected_move_pct,
            "direction": direction,
        }

        return {
            "ticker": t,
            "model": self.model_name,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            # snake_case originals
            "expected_move_pct": expected_move_pct,
            "next_day_expected_move_pct": expected_move_pct,
            "confidence_band": band,
            "confidence_score": score,
            "direction": direction,

            # camelCase aliases
            "expectedMovePct": expected_move_pct,
            "nextDayExpectedMovePct": expected_move_pct,
            "confidenceBand": band,
            "confidenceScore": score,
            "predictedMovePct": expected_move_pct,

            "forecast": forecast,

            # headlines keys (multiple aliases expected by app.py)
            "headlines": headlines,
            "news": headlines,
            "recent_headlines": headlines,
            "recentHeadlines": headlines,
        }


_SINGLETON: PredictionService | None = None


def get_prediction_service() -> PredictionService:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = PredictionService()
    return _SINGLETON


# Load artifacts once at module init
_load_artifacts()

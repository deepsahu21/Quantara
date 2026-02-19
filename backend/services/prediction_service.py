"""
Prediction service (backend/services/prediction_service.py)

Fixes:
- get_prediction_service() takes NO args
- Adds top-level camelCase aliases expected by many React UIs
- Adds headline aliases (recentHeadlines) + keeps existing keys
- Keeps forecast object with both snake_case + camelCase keys
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from backend.services.yfinance_service import get_ohlcv_data
from backend.services.finnhub_service import get_company_news


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _confidence_from_vol(vol_pct: float) -> float:
    # 0.5% daily vol => high confidence, 3% daily vol => low confidence
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


@dataclass
class PredictionService:
    model_name: str = "volatility_baseline"

    def get_prediction(self, ticker: str, days: int = 21) -> Dict[str, Any]:
        t = ticker.upper().strip()
        ohlcv = get_ohlcv_data(t, days=252)

        # Guard
        if not isinstance(ohlcv, list) or len(ohlcv) < 20:
            expected_move_pct = 0.0
            score = 0.50
            band = "Low"
            direction = "flat"
            headlines: List[Dict[str, Any]] = []

            return self._build_response(
                t=t,
                expected_move_pct=expected_move_pct,
                score=score,
                band=band,
                direction=direction,
                headlines=headlines,
            )

        # Compute returns from close
        closes = [float(row.get("close", 0.0)) for row in ohlcv if isinstance(row, dict)]
        rets: List[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            if prev != 0:
                rets.append((closes[i] - prev) / prev)

        # Vol estimate (std of last 60 returns)
        window = rets[-60:] if len(rets) >= 60 else rets
        if not window:
            vol = 0.0
        else:
            mean = sum(window) / len(window)
            var = sum((x - mean) ** 2 for x in window) / max(1, (len(window) - 1))
            vol = var ** 0.5

        vol_pct = abs(vol) * 100.0
        last_ret = rets[-1] if rets else 0.0
        direction = "up" if last_ret > 0 else ("down" if last_ret < 0 else "flat")

        # Simple baseline: magnitude from volatility, sign from last move
        expected_move_pct = (-vol_pct if direction == "down" else (vol_pct if direction == "up" else 0.0))

        score = _confidence_from_vol(vol_pct)
        band = _band(score)

        # Finnhub headlines (empty until FINNHUB_API_KEY is set)
        headlines: List[Dict[str, Any]] = []
        try:
            raw = get_company_news(t, days=7) or []
            headlines = _normalize_headlines(raw)
        except Exception:
            headlines = []

        return self._build_response(
            t=t,
            expected_move_pct=expected_move_pct,
            score=score,
            band=band,
            direction=direction,
            headlines=headlines,
        )

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

        # ---- forecast object (both snake + camel)
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

        # ---- TOP LEVEL (snake + camel aliases)
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

            # camelCase aliases (THIS is what fixes your UI most often)
            "expectedMovePct": expected_move_pct,
            "nextDayExpectedMovePct": expected_move_pct,
            "confidenceBand": band,
            "confidenceScore": score,
            "predictedMovePct": expected_move_pct,

            "forecast": forecast,

            # headlines keys (multiple aliases)
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

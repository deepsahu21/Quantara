"""
Quantara FastAPI backend (backend/app.py)

Matches frontend contract (App.jsx + ForecastPanel.jsx):
/api/prediction/{ticker} returns:
  ohlcv: list
  direction: "bullish"|"bearish"
  confidence_class: "Strong"|"Moderate"|"Low"|"Very Low"
  direction_probability: float (0..1)
  mu_pct: float (decimal, e.g. 0.0112)  # App multiplies by 100
  sentiment_series: list
  headlines: list

Fixes:
- Normalizes headlines to include a usable `date` (from timestamp/datetime).
- Headlines shown in UI stays at 10 items.
- sentiment_series is computed as ONE POINT PER DAY for the last 30 days:
    - value = average sentiment of that day’s articles (sum / count)
    - if count==0, carry-forward the previous day's value (prevents long "0" flatlines)
    - always returns a complete day grid (exactly N points)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.services.prediction_service import get_prediction_service
from backend.services.yfinance_service import get_ohlcv_data
from backend.services.finnhub_service import get_company_news

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quantara_api")

# ------------------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
BACKTEST_DIR = ARTIFACTS_DIR / "backtests"
NEWS_DIR = ARTIFACTS_DIR / "news"

# ------------------------------------------------------------------------------
# Minimal .env loader (no extra dependency)
# ------------------------------------------------------------------------------
def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception as e:
        logger.warning("Failed to load .env from %s: %s", path, e)

_load_dotenv_file(BASE_DIR.parent / ".env")
_load_dotenv_file(BASE_DIR / ".env")

# ------------------------------------------------------------------------------
# App
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Quantara API",
    description="AI-Driven Trading Analytics API",
    version="1.0.0",
)

# ------------------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://quantara-ds.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _mask(s: Optional[str]) -> str:
    if not s:
        return "MISSING"
    s = str(s)
    if len(s) <= 6:
        return "***"
    return f"{s[:3]}***{s[-3:]}"

def _upper_ticker(ticker: str) -> str:
    return ticker.upper().strip()

def _unix_to_ymd(ts: Any) -> str:
    try:
        if isinstance(ts, (int, float)) and ts > 0:
            return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""

def _extract_headline_date(h: Dict[str, Any]) -> str:
    """
    Robust date extraction from many possible headline schemas.
    Returns YYYY-MM-DD or "".
    """
    d = h.get("date")
    if isinstance(d, str) and len(d) >= 10:
        return d[:10]

    dt = h.get("datetime") or h.get("published_at")
    if isinstance(dt, str) and len(dt) >= 10:
        return dt[:10]

    for k in ("timestamp", "datetime", "time", "published", "publishedAt"):
        v = h.get(k)
        ymd = _unix_to_ymd(v)
        if ymd:
            return ymd

    return ""

def _normalize_headlines_for_ui(items: Any) -> List[Dict[str, Any]]:
    """
    Normalize headlines into a stable format:
      headline, title, text, summary, date, timestamp, source, url, sentiment_score
    Ensures `date` exists when timestamp/datetime exists.
    """
    if not isinstance(items, list):
        return []

    out: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue

        headline = it.get("headline") or it.get("title") or it.get("text") or ""
        summary = it.get("summary") or it.get("description") or ""
        ts = it.get("timestamp") or it.get("datetime") or it.get("time") or 0
        ts_int = int(ts) if isinstance(ts, (int, float)) else 0

        date_str = _extract_headline_date({**it, "timestamp": ts_int})

        out.append(
            {
                "headline": headline,
                "title": headline,
                "text": headline,
                "summary": summary,
                "date": date_str,
                "timestamp": ts_int,
                "source": it.get("source") or it.get("publisher") or "",
                "url": it.get("url") or it.get("link") or "",
                "sentiment_score": float(it.get("sentiment_score") or 0.0),
            }
        )

    out = [h for h in out if h.get("headline")]
    try:
        out.sort(key=lambda x: x.get("timestamp", 0) or 0, reverse=True)
    except Exception:
        pass
    return out

# ---- sentiment scoring (improved stem matching; still no extra deps)
_POS_STEMS = {
    "beat", "surge", "soar", "rise", "rally", "jump", "gain", "growth", "profit",
    "record", "strong", "upgrade", "outperform", "bull", "positive", "optimis", "expand",
    "improv", "rebound", "recover", "accelerat"
}
_NEG_STEMS = {
    "miss", "drop", "fall", "slump", "plunge", "crash", "loss", "lawsuit", "probe",
    "investig", "fraud", "cut", "downgrade", "underperform", "bear", "negative",
    "risk", "warn", "weak", "declin", "reduc", "slow"
}

def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.strip(".,:;!?()[]{}\"'").lower() for t in text.split() if t.strip()]

def _stem_hit(tok: str, stems: set[str]) -> bool:
    # cheap stem match: startswith any stem
    for s in stems:
        if tok.startswith(s):
            return True
    return False

def _sent_score(text: str) -> float:
    """
    Returns [-1..1]. More non-zero coverage than strict word equality.
    """
    toks = _tokenize(text)
    if not toks:
        return 0.0

    pos = 0
    neg = 0
    for t in toks:
        if _stem_hit(t, _POS_STEMS):
            pos += 1
        elif _stem_hit(t, _NEG_STEMS):
            neg += 1

    hits = pos + neg
    if hits == 0:
        return 0.0
    return float((pos - neg) / hits)

def _date_range_utc(days: int) -> tuple[date, date]:
    end_d = datetime.utcnow().date()
    start_d = end_d - timedelta(days=days - 1)
    return start_d, end_d

def _to_day(d: str) -> Optional[date]:
    try:
        if isinstance(d, str) and len(d) >= 10:
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    return None

def _midnight_utc_ms(d: date) -> int:
    dt = datetime(d.year, d.month, d.day)
    return int(dt.timestamp() * 1000)

def _sentiment_series_daily(headlines: List[Dict[str, Any]], days: int = 30) -> List[Dict[str, Any]]:
    """
    Exactly one point per day (complete grid), oldest->newest.
    value = avg sentiment for that day (sum/count)
    if no articles that day, carry-forward prior day's value.
    """
    start_d, end_d = _date_range_utc(days)

    # bucket: day -> list of article scores
    buckets: Dict[date, List[float]] = {}
    for h in headlines or []:
        # derive day from timestamp first, then date string
        ts = h.get("timestamp") or 0
        ymd = _unix_to_ymd(ts) if isinstance(ts, (int, float)) else ""
        day = _to_day(ymd) if ymd else _to_day(h.get("date") or _extract_headline_date(h))
        if not day:
            continue
        if day < start_d or day > end_d:
            continue

        text = f"{h.get('headline','') or h.get('text','')} {h.get('summary','')}".strip()
        buckets.setdefault(day, []).append(_sent_score(text))

    series: List[Dict[str, Any]] = []
    prev_val = 0.0

    cur = start_d
    while cur <= end_d:
        vals = buckets.get(cur, [])
        if vals:
            ssum = float(sum(vals))
            cnt = len(vals)
            val = ssum / max(1, cnt)
            prev_val = val
        else:
            # carry-forward avoids “snap to 0” flatlines when there’s no news that day
            ssum = 0.0
            cnt = 0
            val = prev_val

        series.append(
            {
                "x": _midnight_utc_ms(cur),       # numeric x for charts if you want it
                "date": cur.strftime("%Y-%m-%d"), # label used by your current chart
                "value": round(val, 4),
                "score": round(val, 4),
                "count": cnt,
                "sum": round(ssum, 4),
            }
        )
        cur = cur + timedelta(days=1)

    return series

def _pick(pred: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in pred:
            return pred.get(k)
    return None

def _normalize_direction(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in {"bullish", "bull"}:
        return "bullish"
    if s in {"bearish", "bear"}:
        return "bearish"
    if s in {"up", "increase", "rising", "positive"}:
        return "bullish"
    if s in {"down", "decrease", "falling", "negative"}:
        return "bearish"
    return None

def _normalize_conf_class(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    mapping = {
        "strong": "Strong",
        "moderate": "Moderate",
        "low": "Low",
        "very low": "Very Low",
        "very_low": "Very Low",
        "verylow": "Very Low",
    }
    key = s.lower().replace("_", " ")
    return mapping.get(key, s)

def _normalize_prediction_contract(t: str, pred: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make the prediction payload match App.jsx + ForecastPanel.jsx expectations.
    """
    # --- HEADLINES (UI LIST = 10) ---
    pred_headlines = pred.get("headlines")
    headlines_ui = _normalize_headlines_for_ui(pred_headlines) if isinstance(pred_headlines, list) else []

    if not headlines_ui or all(not (h.get("date") or "") for h in headlines_ui):
        headlines_ui = _normalize_headlines_for_ui(get_company_news(t, days=7))

    headlines_ui = (headlines_ui or [])[:10]

    # --- MOVE PCT ---
    fc = pred.get("forecast")
    if isinstance(fc, dict):
        move_pct = _pick(fc, "expected_move_pct", "expectedMovePct", "nextDayExpectedMovePct", "predictedMovePct")
    else:
        move_pct = _pick(pred, "expected_move_pct", "expectedMovePct", "nextDayExpectedMovePct", "predictedMovePct")

    mu_pct = None
    if isinstance(move_pct, (int, float)):
        mu_pct = float(move_pct) / 100.0  # percent -> decimal

    # --- CONFIDENCE SCORE (0..1) ---
    conf_score = _pick(pred, "confidence_score", "confidenceScore")
    if conf_score is None and isinstance(fc, dict):
        conf_score = _pick(fc, "confidence_score", "confidenceScore")
    direction_probability = float(conf_score) if isinstance(conf_score, (int, float)) else None

    # --- CONFIDENCE CLASS ---
    conf_band = _pick(pred, "confidence_band", "confidenceBand")
    if conf_band is None and isinstance(fc, dict):
        conf_band = _pick(fc, "confidence", "confidenceBand", "confidence_band")
    confidence_class = _normalize_conf_class(conf_band)

    # --- DIRECTION ---
    raw_dir = _pick(pred, "direction")
    if raw_dir is None and isinstance(fc, dict):
        raw_dir = _pick(fc, "direction")
    direction = _normalize_direction(raw_dir)

    # --- SENTIMENT SERIES (DAILY GRID; 30 days) ---
    finnhub_news_30 = _normalize_headlines_for_ui(get_company_news(t, days=30))
    sentiment_series = _sentiment_series_daily(finnhub_news_30, days=30)

    # fallback: if Finnhub returns nothing, derive from UI list (still 30-day grid)
    if not finnhub_news_30:
        sentiment_series = _sentiment_series_daily(headlines_ui, days=30)

    # --- OHLCV ---
    try:
        ohlcv = get_ohlcv_data(t, days=420)
        if not isinstance(ohlcv, list):
            ohlcv = []
    except Exception:
        ohlcv = []

    return {
        "ticker": t,
        "generated_at": pred.get("generated_at") or datetime.now().isoformat(timespec="seconds"),

        # REQUIRED BY FRONTEND
        "ohlcv": ohlcv,
        "direction": direction,
        "confidence_class": confidence_class,
        "direction_probability": direction_probability,
        "mu_pct": mu_pct,
        "direction_score": mu_pct,  # fallback path App.jsx uses
        "sentiment_series": sentiment_series,
        "headlines": headlines_ui,

        # Keep raw for debugging
        "raw": pred,
    }

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.get("/api/tickers")
def list_tickers() -> Dict[str, Any]:
    if not BACKTEST_DIR.exists():
        return {"tickers": []}
    return {"tickers": sorted([p.stem for p in BACKTEST_DIR.glob("*.json")])}

@app.get("/api/backtest/{ticker}")
def backtest(ticker: str) -> Dict[str, Any]:
    t = _upper_ticker(ticker)
    path = BACKTEST_DIR / f"{t}.json"
    if not path.exists():
        return {
            "ticker": t,
            "error": f"Backtest artifact not found: {path.name}",
            "backtest_metrics": {},
            "equity_curve": [],
            "benchmark_curve": [],
        }
    data = _read_json(path)
    if not data:
        return {
            "ticker": t,
            "error": f"Backtest artifact read failed: {path.name}",
            "backtest_metrics": {},
            "equity_curve": [],
            "benchmark_curve": [],
        }
    return data

@app.get("/api/ohlcv/{ticker}")
def ohlcv(ticker: str, days: int = 180) -> Any:
    t = _upper_ticker(ticker)
    try:
        return get_ohlcv_data(t, days=int(days))
    except Exception as e:
        logger.exception("OHLCV failed for %s", t)
        raise HTTPException(status_code=500, detail=f"OHLCV failed: {e}")

@app.get("/api/market/{ticker}")
def market_alias(ticker: str, days: int = 180) -> Any:
    return ohlcv(ticker, days)

@app.get("/api/market-data/{ticker}")
def market_data_alias(ticker: str, days: int = 180) -> Any:
    return ohlcv(ticker, days)

@app.get("/api/prices/{ticker}")
def prices_alias(ticker: str, days: int = 180) -> Any:
    return ohlcv(ticker, days)

@app.get("/api/news/{ticker}")
def news(ticker: str, days: int = 7) -> Dict[str, Any]:
    t = _upper_ticker(ticker)

    local_path = NEWS_DIR / f"{t}.json"
    if local_path.exists():
        data = _read_json(local_path)
        if data and isinstance(data.get("headlines"), list):
            return {"ticker": t, "headlines": data["headlines"], "source": "artifact"}

    try:
        headlines = get_company_news(t, days=int(days))
        return {"ticker": t, "headlines": headlines, "source": "finnhub"}
    except Exception as e:
        return {"ticker": t, "headlines": [], "source": "finnhub", "error": str(e)}

@app.get("/api/headlines/{ticker}")
def headlines_alias(ticker: str, days: int = 7) -> Dict[str, Any]:
    return news(ticker, days)

@app.get("/api/recent-headlines/{ticker}")
def recent_headlines_alias(ticker: str, days: int = 7) -> Dict[str, Any]:
    return news(ticker, days)

@app.get("/api/prediction/{ticker}")
def prediction(ticker: str, days: int = 21) -> Dict[str, Any]:
    """
    Returns EXACTLY what your App.jsx expects.
    """
    t = _upper_ticker(ticker)
    try:
        svc = get_prediction_service()
        pred = svc.get_prediction(t, days=int(days))
        if not isinstance(pred, dict):
            raise RuntimeError("prediction_service.get_prediction returned non-dict")
        return _normalize_prediction_contract(t, pred)
    except Exception as e:
        logger.exception("Prediction failed for %s", t)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

@app.get("/api/doctor")
def doctor(ticker: str = "AAPL") -> Dict[str, Any]:
    """
    Diagnostics endpoint to validate backend-to-frontend contract.
    """
    t = _upper_ticker(ticker)

    report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": t,
        "env": {
            "FINNHUB_API_KEY": _mask(os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_KEY")),
        },
        "checks": {},
    }

    # OHLCV
    try:
        data = get_ohlcv_data(t, days=30)
        report["checks"]["ohlcv_type"] = type(data).__name__
        report["checks"]["ohlcv_rows_30d"] = len(data) if isinstance(data, list) else None
        report["checks"]["ohlcv_row0_keys"] = (
            sorted(list(data[0].keys()))
            if isinstance(data, list) and data and isinstance(data[0], dict)
            else []
        )
    except Exception as e:
        report["checks"]["ohlcv_error"] = str(e)

    # Finnhub News
    try:
        h = get_company_news(t, days=30)
        report["checks"]["news_count_30d"] = len(h) if isinstance(h, list) else None
        report["checks"]["news_sample"] = h[0] if isinstance(h, list) and h else None
    except Exception as e:
        report["checks"]["news_error"] = str(e)

    # Prediction contract
    try:
        svc = get_prediction_service()
        pred = svc.get_prediction(t, days=21)
        norm = _normalize_prediction_contract(t, pred if isinstance(pred, dict) else {})
        report["checks"]["prediction_keys"] = sorted(list(norm.keys()))
        report["checks"]["direction"] = norm.get("direction")
        report["checks"]["confidence_class"] = norm.get("confidence_class")
        report["checks"]["direction_probability"] = norm.get("direction_probability")
        report["checks"]["mu_pct"] = norm.get("mu_pct")
        report["checks"]["ohlcv_len"] = len(norm.get("ohlcv") or [])
        report["checks"]["headlines_len"] = len(norm.get("headlines") or [])
        ss = norm.get("sentiment_series") or []
        report["checks"]["sentiment_series_len"] = len(ss)
        report["checks"]["sentiment_first"] = ss[0] if ss else None
        report["checks"]["sentiment_last"] = ss[-1] if ss else None
        report["checks"]["sentiment_nonzero_days"] = sum(1 for p in ss if abs(float(p.get("value") or 0.0)) > 1e-9)
    except Exception as e:
        report["checks"]["prediction_error"] = str(e)

    return report

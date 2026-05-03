"""
Finnhub API Service for Quantara
Handles all external API calls to Finnhub (EXCEPT candlestick OHLCV history)

Fix:
- Do NOT capture FINNHUB_API_KEY at import time.
  Read env var at request-time so app.py's dotenv loader works reliably.

Enhancement:
- Provide DAILY sentiment series (7D / 30D) as one point per day
  using cumulative / aggregate sentiment from all articles that day.
"""

import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json
from dotenv import load_dotenv
import logging

logger = logging.getLogger("finnhub_service")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

# Load environment variables (best-effort; app.py may also load env)
load_dotenv()

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 300  # 5 minutes


# -----------------------------
# Sentiment scoring (lightweight, no deps)
# -----------------------------
_POS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rise", "rises", "strong", "record",
    "profit", "profits", "growth", "upgrade", "bull", "bullish", "outperform", "positive",
    "gain", "gains", "rally", "rebound", "tops", "wins"
}
_NEG = {
    "miss", "misses", "drop", "drops", "fall", "falls", "weak", "lawsuit", "probe", "investigation",
    "fraud", "loss", "losses", "cut", "cuts", "downgrade", "bear", "bearish", "underperform",
    "negative", "risk", "risks", "warning", "warns", "slump", "crash", "plunge"
}


def _sent_score(text: str) -> float:
    """
    Returns sentiment score in [-1, 1] based on keyword hits.
    """
    if not text:
        return 0.0

    toks = [t.strip(".,:;!?()[]{}\"'").lower() for t in text.split()]
    pos = sum(1 for t in toks if t in _POS)
    neg = sum(1 for t in toks if t in _NEG)
    hits = pos + neg
    if hits == 0:
        return 0.0
    return float((pos - neg) / hits)


# -----------------------------
# API key + caching
# -----------------------------
def _get_api_key() -> str:
    """
    Read the API key at call-time (NOT import-time) to avoid module import order issues.
    """
    if not (os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_KEY")):
        try:
            load_dotenv(override=False)
        except Exception:
            pass

    key = os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_KEY")
    if not key:
        raise ValueError("FINNHUB_API_KEY not found in environment variables")
    return key


def _get_cache_key(endpoint: str, params: dict) -> str:
    cache_str = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def _is_cache_valid(cache_entry: dict) -> bool:
    if not cache_entry:
        return False
    return time.time() - cache_entry.get("timestamp", 0) < _cache_ttl


def _get_cached(endpoint: str, params: dict):
    cache_key = _get_cache_key(endpoint, params)
    entry = _cache.get(cache_key)
    if entry and _is_cache_valid(entry):
        return entry.get("data")
    return None


def _set_cache(endpoint: str, params: dict, data):
    cache_key = _get_cache_key(endpoint, params)
    _cache[cache_key] = {"data": data, "timestamp": time.time()}


def _make_request(endpoint: str, params: dict) -> Optional[Any]:
    """
    Make request to Finnhub API with error handling and caching.
    """
    api_key = _get_api_key()

    params_for_cache = dict(params) if params else {}
    cached_data = _get_cached(endpoint, params_for_cache)
    if cached_data is not None:
        return cached_data

    params_with_token = dict(params_for_cache)
    params_with_token["token"] = api_key

    try:
        url = f"{FINNHUB_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params_with_token, timeout=10)

        if response.status_code == 429:
            logger.warning("Finnhub rate limit reached. Using cached data if available.")
            cached_data = _get_cached(endpoint, params_for_cache)
            return cached_data

        response.raise_for_status()
        data = response.json()

        _set_cache(endpoint, params_for_cache, data)
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Finnhub API error: {e}")
        cache_key = _get_cache_key(endpoint, params_for_cache)
        entry = _cache.get(cache_key)
        if entry:
            return entry.get("data")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Finnhub request: {e}")
        return None


# -----------------------------
# Public API
# -----------------------------
def get_quote(symbol: str) -> Optional[Dict]:
    data = _make_request("quote", {"symbol": symbol.upper()})
    if not data or not isinstance(data, dict):
        return None
    return {
        "current": data.get("c", None),
        "high": data.get("h", None),
        "low": data.get("l", None),
        "open": data.get("o", None),
        "prev_close": data.get("pc", None),
        "timestamp": data.get("t", None),
    }


def get_finnhub_now(symbol: str) -> Optional[int]:
    data = _make_request("quote", {"symbol": symbol.upper()})
    if not data or "t" not in data:
        return None
    return int(data["t"])


def get_ohlcv_data(symbol: str, resolution: str = "D", days: int = 180) -> List[Dict]:
    """
    DEPRECATED: Finnhub candles unavailable on your plan. OHLCV comes from yfinance.
    """
    logger.info(
        f"get_ohlcv_data called for '{symbol}'. WARNING: Finnhub candle endpoint not available. Use yfinance."
    )
    return []


def get_company_news(symbol: str, days: int = 7, limit: int = 200) -> List[Dict]:
    """
    Returns a stable, frontend-friendly shape.
    """
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(days=days)

    params = {
        "symbol": symbol.upper(),
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
    }

    data = _make_request("company-news", params)
    if not data or not isinstance(data, list):
        return []

    news_list: List[Dict] = []
    for article in data[: max(1, int(limit))]:
        dt_unix = article.get("datetime", 0)
        if isinstance(dt_unix, (int, float)) and dt_unix > 0:
            dt_iso_date = datetime.utcfromtimestamp(int(dt_unix)).strftime("%Y-%m-%d")
        else:
            dt_iso_date = ""

        headline = article.get("headline", "") or ""
        summary = article.get("summary", "") or ""

        # Provide multiple key variants for robustness
        news_list.append(
            {
                "headline": headline or summary,
                "title": headline or summary,
                "text": headline or summary,
                "summary": summary,
                "date": dt_iso_date,
                "timestamp": dt_unix,
                "source": article.get("source", "") or "",
                "url": article.get("url", "") or "",
                "sentiment_score": 0.0,  # Finnhub doesn't provide per-article sentiment
            }
        )

    news_list.sort(key=lambda x: x.get("timestamp", 0) or 0, reverse=True)
    return news_list


def get_daily_sentiment_series(symbol: str, days: int = 30) -> List[Dict]:
    """
    Returns EXACTLY `days` points: one per calendar day (oldest -> newest).
    Each point aggregates sentiment over all articles that day.

    Output:
      [
        { "date": "YYYY-MM-DD", "value": float, "score": float, "count": int, "label": "YYYY-MM-DD" },
        ...
      ]

    Notes:
    - If a day has no articles, value=0.0 and count=0.
    - "value" is the average sentiment of that day (not sum). If you truly want cum-sum, change below.
    """
    days = max(1, int(days))
    # pull more than needed to reduce "all news clustered in 2 days" effect
    raw = get_company_news(symbol, days=days, limit=500)

    # bucket scores by YYYY-MM-DD
    buckets: Dict[str, List[float]] = {}
    for a in raw:
        d = (a.get("date") or "")[:10]
        if not d:
            continue
        text = f"{a.get('headline','')} {a.get('summary','')}".strip()
        buckets.setdefault(d, []).append(_sent_score(text))

    # build full date range (calendar days)
    end = datetime.utcnow().date()
    start = end - timedelta(days=days - 1)

    series: List[Dict] = []
    cur = start
    while cur <= end:
        key = cur.strftime("%Y-%m-%d")
        vals = buckets.get(key, [])
        if vals:
            avg = sum(vals) / len(vals)
            count = len(vals)
        else:
            avg = 0.0
            count = 0

        series.append(
            {
                "date": key,
                "label": key,
                "value": round(float(avg), 4),
                "score": round(float(avg), 4),
                "count": int(count),
            }
        )
        cur += timedelta(days=1)

    return series

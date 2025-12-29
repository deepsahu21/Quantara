"""
Finnhub API Service for Quantara
Handles all external API calls to Finnhub (EXCEPT candlestick OHLCV history)
"""

import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import json
from dotenv import load_dotenv
import logging

# Setup logging
logger = logging.getLogger("finnhub_service")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'

# In-memory cache with TTL (Time To Live)
_cache = {}
_cache_ttl = 300  # 5 minutes cache


def _get_cache_key(endpoint: str, params: dict) -> str:
    """Generate cache key from endpoint and params"""
    cache_str = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def _is_cache_valid(cache_entry: dict) -> bool:
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    return time.time() - cache_entry.get('timestamp', 0) < _cache_ttl


def _get_cached(endpoint: str, params: dict):
    """Get cached response if available and valid"""
    cache_key = _get_cache_key(endpoint, params)
    entry = _cache.get(cache_key)
    if entry and _is_cache_valid(entry):
        return entry.get('data')
    return None


def _set_cache(endpoint: str, params: dict, data):
    """Store response in cache"""
    cache_key = _get_cache_key(endpoint, params)
    _cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }


def _make_request(endpoint: str, params: dict) -> Optional[Dict]:
    """
    Make request to Finnhub API with error handling and caching.

    Returns:
    --------
    dict: API response data, or None if error
    """
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY not found in environment variables")

    # Always create a copy of params BEFORE adding token
    params_for_cache = dict(params) if params else {}
    cached_data = _get_cached(endpoint, params_for_cache)
    if cached_data is not None:
        return cached_data

    # params may be mutated on request below, so always make a copy!
    params_with_token = dict(params_for_cache)
    params_with_token['token'] = FINNHUB_API_KEY

    try:
        url = f"{FINNHUB_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params_with_token, timeout=10)

        # Handle rate limiting
        if response.status_code == 429:
            logger.warning("Finnhub rate limit reached. Using cached data if available.")
            cached_data = _get_cached(endpoint, params_for_cache)
            return cached_data

        response.raise_for_status()
        data = response.json()

        # Cache successful response
        _set_cache(endpoint, params_for_cache, data)

        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Finnhub API error: {e}")
        # Try to return cached data even if expired
        cache_key = _get_cache_key(endpoint, params_for_cache)
        entry = _cache.get(cache_key)
        if entry:
            return entry.get('data')
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Finnhub request: {e}")
        return None


def get_quote(symbol: str) -> Optional[Dict]:
    """
    Fetches the current price quote for a symbol from Finnhub.

    Returns:
    --------
    dict or None: {
        'current': float,
        'high': float,
        'low': float,
        'open': float,
        'prev_close': float,
        'timestamp': int
    }, or None on error.
    """
    data = _make_request('quote', {'symbol': symbol.upper()})
    if not data or not isinstance(data, dict):
        return None
    # Finnhub: c=current, h=high, l=low, o=open, pc=prevClose, t=ts(unix)
    return {
        'current': data.get('c', None),
        'high': data.get('h', None),
        'low': data.get('l', None),
        'open': data.get('o', None),
        'prev_close': data.get('pc', None),
        'timestamp': data.get('t', None)
    }


def get_finnhub_now(symbol: str) -> Optional[int]:
    """
    Gets the last valid market time from Finnhub for a symbol.

    Returns:
    --------
    int or None: The latest valid market UNIX timestamp from Finnhub, or None if not available.
    """
    data = _make_request('quote', {'symbol': symbol.upper()})
    if not data or 't' not in data:
        return None
    return int(data['t'])


def get_ohlcv_data(symbol: str, resolution: str = 'D', days: int = 180) -> List[Dict]:
    """
    DEPRECATED: Finnhub no longer provides OHLCV historical candles for this plan.
    OHLCV data is now handled via yfinance. This function only returns an empty list to not break callers.

    Parameters:
    -----------
    symbol : str
        Stock ticker symbol (e.g., 'AAPL')
    resolution : str
        (Unused.)
    days : int
        (Unused.)

    Returns:
    --------
    List[Dict]: Always empty list []. OHLCV must come from yfinance.
    """
    logger.info(
        f"get_ohlcv_data called for '{symbol}'. WARNING: Finnhub candle endpoint is not available. OHLCV must come from yfinance."
    )
    return []


def get_company_news(symbol: str, days: int = 7) -> List[Dict]:
    """
    Fetch company news from Finnhub.

    Parameters:
    -----------
    symbol : str
        Stock ticker symbol (e.g., 'AAPL')
    days : int
        Number of days of news to fetch

    Returns:
    --------
    List[Dict]: List of news articles
    """
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    params = {
        'symbol': symbol.upper(),
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d')
    }

    data = _make_request('company-news', params)

    if not data or not isinstance(data, list):
        return []

    # Transform Finnhub response to our format, limit to 10 most recent
    news_list = []
    for article in data[:10]:
        # Extract sentiment score if available (Finnhub doesn't provide this)
        # Placeholder for sentiment score
        sentiment_score = 0.0

        dt_unix = article.get("datetime", 0)
        # Convert Unix seconds to ISO date string
        if isinstance(dt_unix, (int, float)) and dt_unix > 0:
            dt_iso = datetime.utcfromtimestamp(dt_unix).strftime('%Y-%m-%d')
        else:
            dt_iso = ""

        news_list.append({
            'text': article.get('headline', ''),
            'sentiment_score': sentiment_score,
            'date': dt_iso,
            'timestamp': dt_unix,
            'source': article.get('source', ''),
            'url': article.get('url', ''),
            'summary': article.get('summary', '')
        })

    # Sort by date (newest first, using timestamp)
    news_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    return news_list


# The following functions are unused when Finnhub OHLCV is unavailable, but are retained
# for internal compatibility if needed by downstream callers. They are safe no-ops.

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average"""
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(prices[i])  # Use current price until we have enough data
        else:
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(avg)
    return sma


def enrich_ohlcv_with_sma(ohlcv_list: List[Dict]) -> List[Dict]:
    """Enrich OHLCV data with calculated SMA60 and SMA90"""
    # With no OHLCV data, just return
    if not ohlcv_list:
        return ohlcv_list

    closes = [item['close'] for item in ohlcv_list]
    sma60 = calculate_sma(closes, 60)
    sma90 = calculate_sma(closes, 90)

    for i, item in enumerate(ohlcv_list):
        item['sma60'] = round(sma60[i], 2)
        item['sma90'] = round(sma90[i], 2)

    return ohlcv_list


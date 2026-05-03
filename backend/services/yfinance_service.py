import time
import threading
import logging
from typing import List, Dict, Any, Optional

import yfinance as yf
import pandas as pd

# =========================
# CONFIG
# =========================
CACHE_TTL_SECONDS = 300  # 5 minutes
SERVICE_NAME = "yfinance_service"

logger = logging.getLogger(SERVICE_NAME)

# If app.py configures logging, this won't duplicate handlers.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# =========================
# IN-MEMORY CACHE
# =========================
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()
_logged_file_once = False


def _get_cache_key(symbol: str, days: int) -> str:
    return f"{symbol.upper()}:{days}"


def _cache_age_seconds(entry: dict) -> float:
    return time.time() - entry.get("timestamp", 0)


def _is_cache_valid(entry: dict) -> bool:
    if not entry:
        return False
    return _cache_age_seconds(entry) < CACHE_TTL_SECONDS


def _get_cached(symbol: str, days: int):
    cache_key = _get_cache_key(symbol, days)
    with _cache_lock:
        entry = _cache.get(cache_key)
        if entry and _is_cache_valid(entry):
            logger.info(f"[CACHE HIT] key={cache_key} age={_cache_age_seconds(entry):.1f}s rows={len(entry.get('data', []))}")
            return entry.get("data")
        if entry:
            logger.info(f"[CACHE EXPIRED] key={cache_key} age={_cache_age_seconds(entry):.1f}s")
    return None


def _set_cache(symbol: str, days: int, data):
    cache_key = _get_cache_key(symbol, days)
    with _cache_lock:
        _cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
        }
    logger.info(f"[CACHE SET] key={cache_key} rows={len(data)} ttl={CACHE_TTL_SECONDS}s")


def _log_file_once():
    global _logged_file_once
    if not _logged_file_once:
        logger.info(f"🔥 USING yfinance_service FILE: {__file__}")
        _logged_file_once = True


def _normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize yfinance output:
    - Flatten MultiIndex columns if present (e.g., ('Close','AAPL'))
    - Ensure DatetimeIndex is tz-naive UTC for consistent timestamps
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    # Normalize index to UTC-naive timestamps
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        else:
            # treat as UTC already, but ensure tz-naive
            df.index = df.index.tz_localize(None)

    return df


def get_ohlcv_data(symbol: str, days: int = 180) -> List[Dict[str, Any]]:
    """
    Retrieve OHLCV + SMA60/SMA90 using yfinance.
    Returns [] on error / missing ticker / missing columns.
    Fully instrumented for debugging from terminal logs.
    """
    _log_file_once()

    symbol = (symbol or "").upper().strip()
    if not symbol:
        logger.warning("[INPUT] empty symbol")
        return []

    if days <= 0:
        logger.warning(f"[INPUT] invalid days={days}, forcing days=1")
        days = 1

    logger.info(f"[CALL] get_ohlcv_data symbol={symbol} days={days}")

    # -------------------------
    # CACHE CHECK
    # -------------------------
    cached = _get_cached(symbol, days)
    if cached is not None:
        logger.info("[RETURN] cached result")
        return cached

    try:
        # -------------------------
        # DATE WINDOW
        # request extra padding and then trim, so weekends/holidays don't shrink output too much
        # -------------------------
        now_utc = pd.Timestamp.utcnow().normalize()
        start_dt = now_utc - pd.Timedelta(days=days + 14)  # padding
        end_dt = now_utc + pd.Timedelta(days=1)            # inclusive-ish

        logger.info(f"[WINDOW] start={start_dt.date()} end={end_dt.date()} (UTC)")

        # -------------------------
        # DOWNLOAD
        # -------------------------
        logger.info("[YF] calling yf.download ...")

        df = yf.download(
            symbol,
            start=start_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        logger.info(f"[YF] returned df.shape={df.shape}")
        logger.info(f"[YF] raw columns={list(df.columns)}")

        if df is None or df.empty:
            logger.warning("[YF] empty dataframe (ticker may be invalid or no data)")
            _set_cache(symbol, days, [])
            return []

        df = _normalize_ohlcv_df(df)
        logger.info(f"[YF] normalized columns={list(df.columns)}")

        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if not required_cols.issubset(set(df.columns)):
            logger.error(f"[YF] missing required columns required={required_cols} got={set(df.columns)}")
            _set_cache(symbol, days, [])
            return []

        # -------------------------
        # TRIM TO LAST N ROWS
        # -------------------------
        original_len = len(df)
        df = df.tail(days)
        logger.info(f"[TRIM] rows {original_len} -> {len(df)} (target={days})")

        if df.empty:
            logger.warning("[TRIM] dataframe empty after trim")
            _set_cache(symbol, days, [])
            return []

        # -------------------------
        # SMA COMPUTATION
        # -------------------------
        close = df["Close"].astype(float)
        sma60 = close.rolling(window=60, min_periods=1).mean()
        sma90 = close.rolling(window=90, min_periods=1).mean()

        logger.info(
            f"[SMA] last_close={close.iloc[-1]:.4f} last_sma60={sma60.iloc[-1]:.4f} last_sma90={sma90.iloc[-1]:.4f}"
        )

        # -------------------------
        # FORMAT OUTPUT
        # -------------------------
        result: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            # idx is tz-naive UTC timestamp after normalization
            ts = int(pd.Timestamp(idx).timestamp())
            result.append({
                "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                "high": float(row["High"]) if pd.notna(row["High"]) else None,
                "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
                "sma60": round(float(sma60.loc[idx]), 2),
                "sma90": round(float(sma90.loc[idx]), 2),
                "timestamp": ts,
            })

        logger.info(f"[FORMAT] rows={len(result)} first={result[0]['date']} last={result[-1]['date']}")

        _set_cache(symbol, days, result)
        logger.info("[RETURN] success")
        return result

    except Exception as e:
        logger.exception(f"[ERROR] yfinance_service exception: {e}")
        _set_cache(symbol, days, [])
        return []

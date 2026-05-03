"""
backtesting_service.py

Precompute + cache backtests for Quantara tickers.
Strategy (best default):
  - Long (1x) when SMA60 > SMA90
  - Cash (0x) otherwise

Outputs:
  - backtest_metrics: cumulative_pnl, sharpe, max_drawdown, cagr, trades
  - equity_curve: [{t, value, date}]  (frontend can use t to avoid time clutter)
  - benchmark_curve: buy-and-hold equity curve for the same ticker
  - last_period_change: % change over last N points for “+0.3%” style UI

Saves to:
  backend/artifacts/backtests/{TICKER}.json
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.services.yfinance_service import get_ohlcv_data
from backend.utils.data_pipeline import TICKERS  # your S&P100 universe


TRADING_DAYS_PER_YEAR = 252

# Default windows (your timeframe slicing is handled on frontend already)
SMA_FAST = 60
SMA_SLOW = 90

# How far back to pull for backtests (in trading-day terms)
DEFAULT_DAYS = 504  # ~2 years

# Where to cache artifacts
ARTIFACT_DIR = os.path.join("backend", "artifacts", "backtests")


@dataclass
class BacktestResult:
    backtest_metrics: Dict[str, Any]
    equity_curve: List[Dict[str, Any]]
    benchmark_curve: List[Dict[str, Any]]
    last_period_change: Dict[str, float]  # {strategy_pct, benchmark_pct}


def _ensure_artifact_dir() -> None:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except Exception:
        return default


def _ohlcv_list_to_df(ohlcv: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    yfinance_service returns list[dict] with keys like:
      date, open, high, low, close, volume  (and maybe adj_close)
    We normalize + sort by date.
    """
    if not isinstance(ohlcv, list) or len(ohlcv) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(ohlcv).copy()
    # normalize column names (just in case)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    if "date" not in df.columns or "close" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Make sure numeric
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def _compute_max_drawdown(equity: np.ndarray) -> float:
    """
    equity: array of equity values (>=0).
    returns max drawdown as negative number (e.g. -0.23).
    """
    if equity.size == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    drawdown = (equity / peak) - 1.0
    return float(np.min(drawdown))


def _compute_sharpe(daily_returns: np.ndarray) -> float:
    """
    Standard Sharpe with 0 rf.
    """
    if daily_returns.size < 2:
        return 0.0
    mu = np.mean(daily_returns)
    sigma = np.std(daily_returns, ddof=1)
    if sigma == 0 or np.isnan(sigma):
        return 0.0
    return float((mu / sigma) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _compute_cagr(equity: np.ndarray) -> float:
    """
    CAGR from equity curve.
    """
    if equity.size < 2:
        return 0.0
    start = equity[0]
    end = equity[-1]
    if start <= 0:
        return 0.0
    n_days = equity.size - 1
    if n_days <= 0:
        return 0.0
    years = n_days / TRADING_DAYS_PER_YEAR
    if years <= 0:
        return 0.0
    return float((end / start) ** (1.0 / years) - 1.0)


def _last_period_change(equity: np.ndarray, points: int = 21) -> float:
    """
    Percent change over last `points` (default ~1 month of trading days).
    """
    if equity.size < 2:
        return 0.0
    if equity.size <= points:
        base = equity[0]
    else:
        base = equity[-points]
    if base == 0:
        return 0.0
    return float((equity[-1] / base) - 1.0)


def run_backtest_for_ticker(
    ticker: str,
    days: int = DEFAULT_DAYS,
    sma_fast: int = SMA_FAST,
    sma_slow: int = SMA_SLOW,
) -> BacktestResult:
    """
    Compute deterministic long/cash backtest + benchmark for a ticker.
    Returns BacktestResult with metrics + curves.
    """
    # 1) Pull OHLCV from yfinance_service
    ohlcv = get_ohlcv_data(ticker, days=days)

    df = _ohlcv_list_to_df(ohlcv)
    if df.empty or len(df) < max(sma_fast, sma_slow) + 5:
        # not enough data
        empty = BacktestResult(
            backtest_metrics={
                "cumulative_pnl": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "cagr": 0.0,
                "trades": 0,
            },
            equity_curve=[],
            benchmark_curve=[],
            last_period_change={"strategy_pct": 0.0, "benchmark_pct": 0.0},
        )
        return empty

    # 2) Indicators
    df["ret"] = df["close"].pct_change().fillna(0.0)

    df["sma_fast"] = df["close"].rolling(sma_fast).mean()
    df["sma_slow"] = df["close"].rolling(sma_slow).mean()

    # 3) Signal (trend filter) — IMPORTANT: shift by 1 to avoid lookahead bias
    df["signal_raw"] = (df["sma_fast"] > df["sma_slow"]).astype(int)
    df["position"] = df["signal_raw"].shift(1).fillna(0).astype(int)

    # 4) Strategy returns
    df["strategy_ret"] = df["position"] * df["ret"]
    df["benchmark_ret"] = df["ret"]

    # 5) Equity curves (start 1.0)
    df["equity"] = (1.0 + df["strategy_ret"]).cumprod()
    df["benchmark_equity"] = (1.0 + df["benchmark_ret"]).cumprod()

    equity = df["equity"].to_numpy(dtype=float)
    bench = df["benchmark_equity"].to_numpy(dtype=float)
    strat_rets = df["strategy_ret"].to_numpy(dtype=float)

    # 6) Trades (count position flips)
    pos = df["position"].to_numpy(dtype=int)
    # count transitions where position changes
    trades = int(np.sum(np.abs(np.diff(pos))))

    # 7) Metrics
    cumulative_pnl = float(equity[-1] - 1.0)
    sharpe = _compute_sharpe(strat_rets)
    max_dd = _compute_max_drawdown(equity)
    cagr = _compute_cagr(equity)

    # 8) Curves (include `t` index for uncluttered x-axis)
    equity_curve = [
        {"t": int(i), "value": _safe_float(v), "date": d.strftime("%Y-%m-%d")}
        for i, (v, d) in enumerate(zip(df["equity"].tolist(), df["date"]))
    ]
    benchmark_curve = [
        {"t": int(i), "value": _safe_float(v), "date": d.strftime("%Y-%m-%d")}
        for i, (v, d) in enumerate(zip(df["benchmark_equity"].tolist(), df["date"]))
    ]

    last_strat = _last_period_change(equity, points=21)
    last_bench = _last_period_change(bench, points=21)

    return BacktestResult(
        backtest_metrics={
            "cumulative_pnl": round(cumulative_pnl, 4),
            "sharpe": round(sharpe, 3),
            "max_drawdown": round(max_dd, 4),
            "cagr": round(cagr, 4),
            "trades": trades,
        },
        equity_curve=equity_curve,
        benchmark_curve=benchmark_curve,
        last_period_change={
            "strategy_pct": round(last_strat, 4),
            "benchmark_pct": round(last_bench, 4),
        },
    )


def _artifact_path(ticker: str) -> str:
    safe = ticker.replace("/", "_")
    return os.path.join(ARTIFACT_DIR, f"{safe}.json")


def load_cached_backtest(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Load cached artifact JSON if it exists.
    """
    path = _artifact_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_backtest_artifact(ticker: str, result: BacktestResult) -> str:
    """
    Save result to backend/artifacts/backtests/{TICKER}.json
    """
    _ensure_artifact_dir()
    payload = {
        "ticker": ticker,
        "strategy": {
            "type": "SMA_CROSS_LONG_CASH",
            "sma_fast": SMA_FAST,
            "sma_slow": SMA_SLOW,
        },
        "backtest_metrics": result.backtest_metrics,
        "equity_curve": result.equity_curve,
        "benchmark_curve": result.benchmark_curve,
        "last_period_change": result.last_period_change,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = _artifact_path(ticker)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def get_or_compute_backtest(
    ticker: str,
    force_recompute: bool = False
) -> Dict[str, Any]:
    """
    Used by API:
      - return cached instantly if present
      - otherwise compute + save + return
    """
    if not force_recompute:
        cached = load_cached_backtest(ticker)
        if cached is not None:
            return cached

    result = run_backtest_for_ticker(ticker)
    save_backtest_artifact(ticker, result)
    return load_cached_backtest(ticker) or {}


def precompute_all_backtests(
    tickers: Optional[List[str]] = None,
    force_recompute: bool = False
) -> Tuple[int, int]:
    """
    Batch precompute for S&P100 tickers.
    Returns (success_count, fail_count).
    """
    _ensure_artifact_dir()
    universe = tickers or list(TICKERS)
    ok = 0
    fail = 0

    for t in universe:
        try:
            print(f"🔄 Backtesting {t}")
            if not force_recompute:
                # skip if already exists
                if os.path.exists(_artifact_path(t)):
                    print(f"✅ Cached exists, skipping: {t}")
                    ok += 1
                    continue

            res = run_backtest_for_ticker(t)
            path = save_backtest_artifact(t, res)
            print(f"💾 Saved {t} -> {path}")
            ok += 1
        except Exception as e:
            print(f"❌ Failed {t}: {e}")
            fail += 1

    print(f"\nDONE ✅ success={ok} fail={fail}")
    return ok, fail


if __name__ == "__main__":
    # Run batch job:
    #   python -m backend.services.backtesting_service
    #
    # Optional: set force_recompute=True to overwrite cached JSONs
    precompute_all_backtests(force_recompute=False)

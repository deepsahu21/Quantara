import numpy as np
import pandas as pd
from typing import Dict, Any

from services.yfinance_service import get_ohlcv_data
from services.prediction_service import get_prediction_service


TRADING_DAYS_PER_YEAR = 252


def run_backtest_for_ticker(
    ticker: str,
    lookback_days: int = 504  # ~2 years
) -> Dict[str, Any]:
    """
    Runs a simple historical backtest for a single ticker.

    Strategy:
    - Each day, use historical data up to that day
    - If model predicts bullish → buy next day open, sell next day close
    - If bearish → stay in cash

    Returns metrics + equity curve for UI.
    """

    # --------------------------------------------------
    # 1️⃣ Load historical OHLCV
    # --------------------------------------------------
    df = get_ohlcv_data(ticker, days=lookback_days)

    if df is None or len(df) < 50:
        return _empty_backtest()

    df = df.sort_values("date").reset_index(drop=True)

    # --------------------------------------------------
    # 2️⃣ Initialize model
    # --------------------------------------------------
    predictor = get_prediction_service()

    returns = []
    equity = [1.0]
    dates = []

    # --------------------------------------------------
    # 3️⃣ Walk forward in time (NO LOOKAHEAD)
    # --------------------------------------------------
    for i in range(30, len(df) - 1):
        history = df.iloc[:i].copy()
        today = df.iloc[i]
        tomorrow = df.iloc[i + 1]

        # Model prediction using data up to today
        pred = predictor.predict_from_dataframe(
            history, ticker=ticker
        )

        signal = pred.get("direction", "bearish")

        # --------------------------------------------------
        # Trading rule
        # --------------------------------------------------
        if signal == "bullish":
            daily_return = (
                tomorrow["close"] / tomorrow["open"] - 1
            )
        else:
            daily_return = 0.0

        returns.append(daily_return)
        equity.append(equity[-1] * (1 + daily_return))
        dates.append(tomorrow["date"])

    returns = np.array(returns)
    equity = np.array(equity[1:])  # drop initial seed

    # --------------------------------------------------
    # 4️⃣ Metrics
    # --------------------------------------------------
    cumulative_pnl = equity[-1] - 1

    trades = int(np.sum(returns != 0))

    if np.std(returns) > 0:
        sharpe = (
            np.mean(returns)
            / np.std(returns)
            * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
    else:
        sharpe = 0.0

    # Max drawdown
    running_max = np.maximum.accumulate(equity)
    drawdowns = (equity - running_max) / running_max
    max_drawdown = float(drawdowns.min())

    # CAGR
    total_days = len(equity)
    years = total_days / TRADING_DAYS_PER_YEAR
    cagr = (
        equity[-1] ** (1 / years) - 1
        if years > 0 else 0.0
    )

    # --------------------------------------------------
    # 5️⃣ Package results
    # --------------------------------------------------
    equity_curve = [
        {"date": d, "value": float(v)}
        for d, v in zip(dates, equity)
    ]

    return {
        "backtest_metrics": {
            "cumulative_pnl": round(float(cumulative_pnl), 4),
            "sharpe": round(float(sharpe), 3),
            "max_drawdown": round(float(max_drawdown), 4),
            "cagr": round(float(cagr), 4),
            "trades": trades
        },
        "equity_curve": equity_curve
    }


def _empty_backtest() -> Dict[str, Any]:
    """
    Safe fallback when data is insufficient.
    """
    return {
        "backtest_metrics": {
            "cumulative_pnl": None,
            "sharpe": None,
            "max_drawdown": None,
            "cagr": None,
            "trades": 0
        },
        "equity_curve": []
    }

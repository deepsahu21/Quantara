# backend/utils/feature_engineering.py

import pandas as pd

INPUT_PATH = "backend/data/processed_data/merged_data.csv"
OUTPUT_PATH = "backend/data/processed_data/feature_data.csv"

LAGS = [1]
ROLLING_WINDOW = 14


def build_features():
    df = pd.read_csv(INPUT_PATH, parse_dates=["date"])
    df = df.sort_values(["ticker", "date"])

    # -----------------------------
    # Lag features
    # -----------------------------
    for lag in LAGS:
        df[f"open_price_lag{lag}"] = df.groupby("ticker")["open_price"].shift(lag)
        df[f"high_price_lag{lag}"] = df.groupby("ticker")["high_price"].shift(lag)
        df[f"low_price_lag{lag}"] = df.groupby("ticker")["low_price"].shift(lag)
        df[f"close_price_lag{lag}"] = df.groupby("ticker")["close_price"].shift(lag)
        df[f"volume_lag{lag}"] = df.groupby("ticker")["volume"].shift(lag)
        df[f"sentiment_score_lag{lag}"] = df.groupby("ticker")["sentiment_score"].shift(lag)
        df[f"polarity_lag{lag}"] = df.groupby("ticker")["polarity"].shift(lag)
        df[f"headline_count_lag{lag}"] = df.groupby("ticker")["headline_count"].shift(lag)

    # -----------------------------
    # Returns + rolling volatility
    # -----------------------------
    df["daily_return"] = df.groupby("ticker")["close_price"].pct_change()

    df["rolling_vol"] = (
        df.groupby("ticker")["daily_return"]
          .rolling(ROLLING_WINDOW)
          .std()
          .reset_index(level=0, drop=True)
    )

    # -----------------------------
    # Calendar features
    # -----------------------------
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year

    # -----------------------------
    # Target (next-day return)
    # -----------------------------
    df["target_pct_change"] = df.groupby("ticker")["daily_return"].shift(-1)

    # -----------------------------
    # Cleanup
    # -----------------------------
    df = df.dropna().reset_index(drop=True)

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Feature data written to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_features()

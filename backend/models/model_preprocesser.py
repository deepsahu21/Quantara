# backend/models/model_preprocessor.py

import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder

FEATURE_DATA_PATH = "backend/data/processed_data/feature_data.csv"


def load_model_data(return_meta: bool = False, return_schema: bool = False):
    df = pd.read_csv(FEATURE_DATA_PATH)

    # -----------------------------
    # Target
    # -----------------------------
    y = df["target_pct_change"].values

    # -----------------------------
    # Base features (keep ticker for encoding)
    # -----------------------------
    X = df.drop(columns=["target_pct_change", "date"]).copy()

    # -----------------------------
    # Encode ticker
    # -----------------------------
    ticker_encoder = LabelEncoder()
    X["encoded_ticker"] = ticker_encoder.fit_transform(X["ticker"])
    X = X.drop(columns=["ticker"])

    # -----------------------------
    # Save schema BEFORE scaling
    # -----------------------------
    feature_schema = list(X.columns)

    # -----------------------------
    # Scale features (fit on 80% train split only to prevent leakage)
    # -----------------------------
    split_idx = int(len(X) * 0.8)
    scaler = StandardScaler()
    scaler.fit(X.iloc[:split_idx])
    X_scaled = pd.DataFrame(
        scaler.transform(X),
        columns=feature_schema
    )

    meta = {
        "dates": df["date"].values if "date" in df.columns else None,
        "tickers": df["ticker"].values if "ticker" in df.columns else None,
        "target_pct_change": df["target_pct_change"].values,
    }

    if return_meta and return_schema:
        return X_scaled, y, scaler, ticker_encoder, meta, feature_schema

    if return_meta:
        return X_scaled, y, scaler, ticker_encoder, meta

    if return_schema:
        return X_scaled, y, scaler, ticker_encoder, feature_schema

    return X_scaled, y, scaler, ticker_encoder

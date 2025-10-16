import pandas as pd
from sklearn.preprocessing import LabelEncoder




def preprocess_data(file_path):
    
    df = pd.read_csv(file_path)
    # ...CONVERT DATE...

    df["date"] = pd.to_datetime(df['date'])

    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.weekday    # 0 = Monday, 6 = Sunday
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year

    #Adding time index
    df["time_index"] = df["date"].map(pd.Timestamp.toordinal)

    #drop original column
    df = df.drop(columns = ["date"])


    # ...ENCODE CATEGORICAL VARIABLES...

    encoder = LabelEncoder()
    df["encoded_ticker"] = encoder.fit_transform(df["ticker"])
    df = df.drop(columns = ["ticker"])
    
    # ... Shift and create lag columns... 
    group = df.groupby("encoded_ticker")

    lag_cols = ["open_price", "high_price", "low_price", "close_price", "volume",
                "sentiment_score", "polarity", "headline_count"]

    for col in lag_cols:
        df[f"{col}_lag1"] = group[col].shift(1)
    
    df = df.dropna(subset=["open_price_lag1", "close_price_lag1"]) #delete rows with NaN lag values

    # ... Define feature columns ...
    feature_cols = [
        # prices known after market opens
        "open_price",
        "open_price_lag1", "high_price_lag1", "low_price_lag1",
        "close_price_lag1", "volume_lag1",
        # news sentiment — current & lagged
        "sentiment_score", "polarity", "headline_count",
        "sentiment_score_lag1", "polarity_lag1", "headline_count_lag1",
        # calendar & meta
        "day", "day_of_week", "month", "quarter", "year",
        "time_index", "encoded_ticker"
]
    df_final = df[feature_cols + ["close_price"]].copy()

    return df_final


if __name__ == "__main__":
    input_path = "backend/data/processed_data/merged_data.csv"
    output_path = "backend/data/processed_data/final_processed_data.csv"
    
    processed_df = preprocess_data(input_path)
    processed_df.to_csv(output_path, index = False)



    

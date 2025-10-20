import pandas as pd
from sklearn.preprocessing import LabelEncoder


input_path = "backend/data/processed_data/merged_data.csv"
output_path = "backend/data/processed_data/final_processed_data.csv"

def convert_date(df):
    
    #Convert date and extract date features
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

    print("date converted")
    return df



def encode_variables(df):
    encoder = LabelEncoder()
    df["encoded_ticker"] = encoder.fit_transform(df["ticker"])
    df = df.drop(columns = ["ticker"])

    print("variabled encoded")
    return df



def create_lag_features(df):

    group = df.groupby("encoded_ticker")

    lag_cols = ["open_price", "high_price", "low_price", "close_price", "volume",
                "sentiment_score", "polarity", "headline_count"]

    for col in lag_cols:
        df[f"{col}_lag1"] = group[col].shift(1)
    
    df = df.dropna(subset=["open_price_lag1", "close_price_lag1"]) #delete rows with NaN lag values

    print("lag features created")
    return df



def add_calculated_features(df):

    group = df.groupby("encoded_ticker")

     # Add sentiment change column 
    df["sentiment_change"] = df["sentiment_score"] - df["sentiment_score_lag1"]

    # Percentage change of close price
    df["pct_change"] = group["close_price"].pct_change() * 100

    # Target = next day’s percentage change
    df["target_pct_change"] = group["pct_change"].shift(-1)

    df = df.dropna(subset=["target_pct_change"])

    print("calculated features added")
    return df



def create_final_df(df):

    feature_cols = [
        # prices known after market opens
        "open_price", "close_price",
        # lagged prices & volume
        "open_price_lag1", "high_price_lag1", "low_price_lag1",
        "close_price_lag1", "volume_lag1",
        # news sentiment: current & lagged
        "sentiment_score", "polarity", "headline_count",
        "sentiment_score_lag1", "polarity_lag1", "headline_count_lag1",
        # calendar & meta
        "day", "day_of_week", "month", "quarter", "year",
        "time_index", "encoded_ticker",
        # Calculated features
        "sentiment_change",
    ]

   
    
    # merge dependent and independent variables
    df_final = df[feature_cols + ["target_pct_change"]].copy()

    print("final dataframe created")
    return df_final


if __name__ == "__main__":
    
    df = pd.read_csv(input_path)

    df = convert_date(df)
    df = encode_variables(df)
    df = create_lag_features(df)
    df = add_calculated_features(df)
    processed_df = create_final_df(df)
    processed_df.to_csv(output_path, index = False)
    print("Done!")



    

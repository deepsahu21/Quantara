import pandas as pd
from sklearn.preprocessing import LabelEncoder



def preprocess_data(df):
    
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
    
    return df


    

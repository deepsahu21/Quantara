import pandas as pd
from data_pipeline import TICKERS



file_path = "C:/temp/news_raw.csv" 
trimmed_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/news_raw.csv"

df = pd.read_csv(file_path, usecols = ["Date", "Article_title", "Stock_symbol"])
df = df[df["Stock_symbol"].isin(TICKERS)]

df["Date"] = pd.to_datetime(df["Date"]).dt.date
print(df.head(3))
df.to_csv(trimmed_path, index = False)






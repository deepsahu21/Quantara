import pandas as pd

df = pd.read_csv("C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/all_stocks_long.csv")

# Look for rows where date isn’t YYYY-MM-DD
bad_dates = df[~df["date"].astype(str).str.match(r"\d{4}-\d{2}-\d{2}")]
print(bad_dates)

# Look for weird volume entries
bad_volume = df[~df["volume"].astype(str).str.match(r"^\d+(\.0)?$")]
print(bad_volume)
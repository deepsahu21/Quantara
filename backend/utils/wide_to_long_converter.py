import pandas as pd


#Path to the wide format file
wide_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/raw_data/stocks.csv"

#Read the wide format CSV
df = pd.read_csv(wide_path, header = [0,1])

dates = df.iloc[:, 0]
data_rows = []


#Iterate over all of the other columns
for ticker, field in df.columns[1:]:
    values = df[(ticker, field)]
    for date, val in zip(dates, values):
        data_rows.append([date,ticker, field, val])

#Turn the list of rows into a dataframe
long_df = pd.DataFrame(data_rows, columns = ["date", "ticker", "field", "values"])

#Pivot the dataframe turning field into a column

long_df = long_df.pivot(

    index = ["date", "ticker"],
    columns = "field",
    values = "values"
).reset_index()

#Rename the columns to match the psql schema

long_df = long_df.rename(columns={
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "close_price",
    "Volume": "volume"
})

#Reorder the columns
long_df = long_df[["date","ticker","open_price","high_price","low_price","close_price","volume"]]

#Drop NaN values
long_df = long_df.dropna(subset=["open_price", "high_price", "low_price", "close_price", "volume"])

#Save the output
output_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/all_stocks_long.csv"
long_df.to_csv(output_path, index = False)

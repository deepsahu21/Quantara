import pandas as pd


#Path to the wide format file
wide_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/raw_data/stocks.csv"

#Read the wide format CSV
df = pd.read_csv(wide_path, header = [0,1])
print(df.columns)


#Rename the first column
df = df.rename(columns={df.columns[0]: "date"})


#Convert to long format
long_df = df.melt(
    id_vars = ["date"],
    var_name = ["ticker", "field"],
    value_name = "value"
)


long_df = long_df.pivot_table(

    index = ["date", "ticker"],
    columns = "field",
    values = "value"
).reset_index()

#rename columns
long_df = long_df.rename(columns = {

    "Open" : "open_price",
    "High" : "high_price",
    "Low" : "low_price",
    "Close" : "close_price",
    "Volume" : "volume"
})

long_df = long_df[["date", "ticker", "open_price", "high_price", "low_price", "close_price", "volume"]]

output_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/all_stocks.csv"
long_df.to_csv(output_path, index = False)
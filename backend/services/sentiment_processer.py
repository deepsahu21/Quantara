import pandas as pd

file_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/raw_data/news_with_sentiment.csv"
output_path = "C:/Users/deeps/Desktop/projects/Quantara/backend/data/processed_data/daily_sentiment.csv"
def daily_sentiment_cleaner(input_file, output_file):
    news = pd.read_csv(input_file)

    #one hot encoding 
    labels = pd.get_dummies(news["predicted_label"])
    news = pd.concat([news, labels], axis = 1)


    #Grouping the tickers and dates
    agg = news.groupby(["Stock_symbol", 'Date']).agg(
        avg_strength = ("sentiment_strength", "mean"),
        pct_positive = ("positive", "mean"),
        pct_negative = ("negative", "mean"),
        headline_count = ("Article_title", "count")
    ).reset_index()

    #set polarity variable
    agg["polarity"] = agg["pct_positive"] - agg["pct_negative"]

    #Keep only relevant columns
    agg = agg[["Date", "Stock_symbol", "avg_strength", "polarity", "headline_count"]]
    agg.to_csv(output_file, index =False)

if __name__ == "__main__":
    daily_sentiment_cleaner(file_path, output_path)

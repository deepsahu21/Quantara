#File for processing sentiment analysis on news articles
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

#Load FinBERT model

MODEL_NAME = "ProsusAI/finbert"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
model.to("cuda")

model.eval()

labels = ["positive", "negative", "neutral"]

#Scores the sentiment of the given article


def analyze_sentiment(article : str):
    global count
    count += 1
    if count  % 1000 == 0:
        print(f"Processed {count} articles")

    inputs = tokenizer(article, return_tensors = "pt", truncation = True, padding = True).to("cuda")

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

    label_index = int(torch.argmax(probs))
    predicted_label = labels[label_index]
    sentiment_strength = float(probs[label_index])

    return {
        "predicted_label": predicted_label,
        "sentiment_strength": sentiment_strength
    }

if __name__ == "__main__":
    count = 1
    news = pd.read_csv("backend/data/news_raw.csv")
    #print("read news file")

    sentiment_results = news["Article_title"].apply(analyze_sentiment).apply(pd.Series)
    #print("applied sentiment analysis")

    news_with_sentiment = pd.concat([news, sentiment_results], axis=1)
    #print("combined rows")

    news_with_sentiment.to_csv("backend/data/news_with_sentiment.csv", index = False)
    #print("Saved file")
    



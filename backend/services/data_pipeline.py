#Creates CSV files for each stock in the TICKERS list and saves them into the data/stocks directory.
import os
from datetime import date
import yfinance as yf

DATA_DIR = "src/data/stocks"
start_date = "2020-01-01"
end_date = date.today().strftime("%Y-%m-%d")
interval = "1d"

TICKERS = [
    "AAPL","ABBV","ABT","ACN","ADBE","AIG","AMD","AMGN","AMT","AMZN",
    "AVGO","AXP","BA","BAC","BK","BKNG","BLK","BMY","BRK.B","C",
    "CAT","CHTR","CL","CMCSA","COF","COP","COST","CRM","CSCO","CVS",
    "CVX","DE","DHR","DIS","DUK","EMR","FDX","GD","GE","GILD",
    "GM","GOOG","GOOGL","GS","HD","HON","IBM","INTC","INTU","ISRG",
    "JNJ","JPM","KO","LIN","LLY","LMT","LOW","MA","MCD","MDLZ",
    "MDT","MET","META","MMM","MO","MRK","MS","MSFT","NEE","NFLX",
    "NKE","NOW","NVDA","ORCL","PEP","PFE","PG","PLTR","PM","PYPL",
    "QCOM","RTX","SBUX","SCHW","SO","SPG","T","TGT","TMO","TMUS",
    "TSLA","TXN","UNH","UNP","UPS","USB","V","VZ","WFC","WMT","XOM"
]


def get_stock_data(tickers):
    data = yf.download(tickers, start = start_date, end = end_date, interval = interval, group_by = 'ticker')
    return data

def save_to_csv(data, tickers):
    for ticker in tickers:
        if ticker in data:
            ticker_data = data[ticker].dropna()
            filepath = os.path.join(DATA_DIR, f"{ticker}.csv")
            ticker_data.to_csv(filepath)
            print(f"Saved{ticker} to stocks/")

    


if __name__ == "__main__":
    
    stock_data = get_stock_data(TICKERS)
    save_to_csv(stock_data, TICKERS)
    



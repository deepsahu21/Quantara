#Creates CSV files for each stock in the TICKERS list and saves them into the data/stocks directory.
import os
from datetime import date
import yfinance as yf

DATA_DIR = "backend/data/"
start_date = "2020-01-01"
end_date = date.today().strftime("%Y-%m-%d")
interval = "1d"

TICKERS = [
    "AAPL","ABBV","ABT","ACN","ADBE","AIG","AMD","AMGN","AMT","AMZN",
    "AVGO","AXP","BA","BAC","BK","BKNG","BLK","BMY","BRK-B","C",
    "CAT","CHTR","CL","CMCSA","COF","COP","COST","CRM","CSCO","CVS",
    "CVX","DE","DHR","DIS","DUK","EMR","FDX","GD","GE","GILD",
    "GM","GOOG","GOOGL","GS","HD","HON","IBM","INTC","INTU","ISRG",
    "JNJ","JPM","KO","LIN","LLY","LMT","LOW","MA","MCD","MDLZ",
    "MDT","MET","META","MMM","MO","MRK","MS","MSFT","NEE","NFLX",
    "NKE","NOW","NVDA","ORCL","PEP","PFE","PG","PLTR","PM","PYPL",
    "QCOM","RTX","SBUX","SCHW","SO","SPG","T","TGT","TMO","TMUS",
    "TSLA","TXN","UNH","UNP","UPS","USB","V","VZ","WFC","WMT","XOM"
]

# Downloads stock data from Yahoo Finance
def get_stock_data(tickers):
    data = yf.download(tickers, start = start_date, end = end_date, interval = interval, group_by = 'ticker')
    data[]
    return data

    


if __name__ == "__main__":
    
    stock_data = get_stock_data(TICKERS)
    stock_data.to_csv(os.path.join(DATA_DIR, "all_stocks.csv"))
    



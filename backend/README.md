# Quantara Backend API

FastAPI backend for Quantara AI-Driven Trading Analytics Dashboard.

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
   
   Create a `.env` file in the `backend/` directory:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Finnhub API key:
   ```
   FINNHUB_API_KEY=your_api_key_here
   ```
   
   Get your free API key from: https://finnhub.io/register

3. **Run the server:**
```bash
python app.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET `/api/prediction/{ticker}`
Get complete prediction data for a ticker (includes OHLCV, news, sentiment, etc.)

**Example:**
```bash
curl http://localhost:8000/api/prediction/AAPL
```

### GET `/api/market/{ticker}`
Get OHLCV candlestick data for a ticker

**Query Parameters:**
- `days` (optional): Number of days of historical data (default: 180)

**Example:**
```bash
curl http://localhost:8000/api/market/AAPL?days=90
```

### GET `/api/news/{ticker}`
Get company news for a ticker

**Query Parameters:**
- `days` (optional): Number of days of news to fetch (default: 7)

**Example:**
```bash
curl http://localhost:8000/api/news/AAPL?days=30
```

### GET `/api/tickers`
Get list of available tickers

## Data Sources

- **Market Data**: Finnhub API (OHLCV candlestick data)
- **News**: Finnhub API (company news)
- **Predictions**: Internal ML models (when available)

## Caching

The Finnhub service implements in-memory caching with a 5-minute TTL to:
- Reduce API calls
- Handle rate limits gracefully
- Improve response times

## Error Handling

- API errors are logged and cached data is returned when available
- Rate limits (429) trigger fallback to cached data
- Missing data returns empty arrays instead of errors

## Security

- API keys are never exposed to the frontend
- All external API calls are made server-side only
- Environment variables are loaded securely using python-dotenv


# Quantara Finnhub Integration Setup Guide

This guide explains how to set up the Quantara dashboard with real Finnhub market data and news.

## Prerequisites

1. Python 3.8+ installed
2. Node.js 16+ and npm installed
3. A Finnhub API key (free tier available at https://finnhub.io/register)

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cd backend
touch .env
```

Add your Finnhub API key to the `.env` file:

```
FINNHUB_API_KEY=your_actual_api_key_here
```

**Important:** 
- Never commit the `.env` file to git (it's already in .gitignore)
- The API key is only used server-side and never exposed to the frontend

### 3. Start the Backend Server

```bash
python app.py
```

The API will run on `http://localhost:8000`

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start the Development Server

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Verification

### Test Backend Endpoints

1. **Health Check:**
   ```bash
   curl http://localhost:8000/
   ```
   Should return: `{"status":"ok","service":"Quantara API"}`

2. **Market Data:**
   ```bash
   curl http://localhost:8000/api/market/AAPL
   ```
   Should return OHLCV data for Apple

3. **News:**
   ```bash
   curl http://localhost:8000/api/news/AAPL
   ```
   Should return recent news articles

4. **Full Prediction:**
   ```bash
   curl http://localhost:8000/api/prediction/AAPL
   ```
   Should return complete prediction data with OHLCV and news

### Test Frontend

1. Open `http://localhost:3000` in your browser
2. Select a ticker (e.g., AAPL)
3. Verify:
   - Candlestick chart loads with real price data
   - News headlines appear in the bottom right panel
   - Sentiment chart displays (may be empty if no sentiment analysis yet)

## API Key Security

✅ **Correct:**
- API key stored in `.env` file (server-side only)
- Backend makes all Finnhub API calls
- Frontend only calls backend endpoints
- API key never appears in browser network tab

❌ **Incorrect:**
- Hard-coding API key in source code
- Frontend calling Finnhub directly
- Exposing API key in frontend environment variables

## Troubleshooting

### "FINNHUB_API_KEY not found"
- Ensure `.env` file exists in `backend/` directory
- Check that the file contains: `FINNHUB_API_KEY=your_key_here`
- Restart the backend server after creating/editing `.env`

### "No market data available"
- Verify your Finnhub API key is valid
- Check Finnhub API status: https://finnhub.io/api-status
- Verify you haven't exceeded rate limits (free tier: 60 calls/minute)

### "Failed to load prediction data"
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify backend logs for API errors

### Empty charts or data
- Finnhub free tier has rate limits
- Data is cached for 5 minutes to reduce API calls
- Try refreshing after a few seconds

## Caching

The backend implements intelligent caching:
- **Cache Duration:** 5 minutes
- **Cache Scope:** Per endpoint and parameters
- **Rate Limit Handling:** Falls back to cached data when rate limited

This means:
- First request fetches from Finnhub
- Subsequent requests within 5 minutes use cached data
- Reduces API calls and improves performance

## Next Steps

1. **Connect Real ML Models:** Update `prediction_service.py` to use your trained models
2. **Add Sentiment Analysis:** Integrate FinBERT to analyze news sentiment
3. **Implement Backtesting:** Connect real backtest results to the dashboard
4. **Add More Tickers:** Expand the ticker list in the frontend

## Support

For Finnhub API issues:
- Documentation: https://finnhub.io/docs/api
- Status: https://finnhub.io/api-status
- Support: support@finnhub.io


# Quantara Frontend Dashboard

Institutional-grade AI stock analytics dashboard with dark-mode Bloomberg-inspired design.

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Start the development server:
```bash
npm run dev
# or
yarn dev
```

The dashboard will be available at `http://localhost:3000`

## Backend Setup

Make sure the backend API is running on `http://localhost:8000`:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

## Features

- **Dark Theme**: Professional Bloomberg-inspired dark mode
- **Real-time Predictions**: AI-driven direction and confidence signals
- **Interactive Charts**: Candlestick charts with volume and moving averages
- **Sentiment Analysis**: News sentiment trends over time
- **Backtest Metrics**: Historical simulation performance
- **Headlines**: Recent news with sentiment scores

## Data Contract

The frontend expects API responses matching this structure:

```json
{
  "ticker": "AAPL",
  "direction_score": 0.67,
  "direction": "bullish",
  "confidence_band": 0.78,
  "confidence_class": "Moderate",
  "feature_attribution": {
    "historical": 0.70,
    "sentiment": 0.30
  },
  "sentiment_series": [...],
  "ohlcv": [...],
  "backtest_metrics": {...},
  "headlines": [...]
}
```

## Tech Stack

- React 18
- Vite
- Recharts (charting)
- Axios (API calls)



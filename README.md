<div align="center">

# Quantara

### AI-Driven Trading Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)

**Quantara** fuses real-time market data, news sentiment analysis, and machine-learning forecasts into a single, interactive dashboard — giving you the clarity to make smarter trading decisions.

[Getting Started](#-getting-started) · [Features](#-features) · [Architecture](#-architecture) · [API Reference](#-api-reference)

</div>

---

![Quantara Dashboard](examples/dashboard_full.png)

> *Screenshot: the Quantara dashboard showing AAPL with candlestick chart, forecast panel, sentiment trend, backtest metrics, and real-time headlines.*

---

## ✨ Features

| Module | What it does |
|---|---|
| **Candlestick Chart** | Interactive OHLCV chart with volume overlay and configurable timeframes (1 D → 1 Y). |
| **Forecast Panel** | Next-day directional prediction (bullish / bearish) with confidence band and expected move percentage. |
| **Sentiment Analysis** | 30-day rolling sentiment score derived from financial news, displayed as a time-series chart. |
| **Backtesting Engine** | Historical strategy performance — cumulative PnL, Sharpe ratio, max drawdown, CAGR, and an equity curve chart. |
| **Headlines Feed** | Latest scored headlines for the selected ticker, sourced from Finnhub. |
| **Ticker Search** | Instant search across all tracked equities. |

---

## � Dashboard Panels

<table>
  <tr>
    <td width="50%">
      <img src="examples/chart_forecast.png" alt="Chart & Forecast" />
      <p align="center"><em>Candlestick chart with forecast panel and sentiment trend</em></p>
    </td>
    <td width="50%">
      <img src="examples/backtest_headlines.png" alt="Backtest & Headlines" />
      <p align="center"><em>Backtest metrics, equity curve, and scored headlines</em></p>
    </td>
  </tr>
</table>

---

## 🏗 Architecture

```
Quantara/
├── backend/                       # Python / FastAPI server
│   ├── app.py                     # API entry point & route definitions
│   ├── models/                    # ML model training & inference
│   │   ├── model.py               # Primary forecasting model
│   │   ├── baseline_models.py     # Baseline comparison models
│   │   ├── evaluate.py            # Model evaluation pipeline
│   │   ├── feature_engineering.py # Feature transforms
│   │   └── model_preprocesser.py  # Data preprocessing
│   ├── services/                  # Modular backend services
│   │   ├── prediction_service.py  # ML prediction orchestration
│   │   ├── yfinance_service.py    # OHLCV data via yfinance
│   │   ├── finnhub_service.py     # News & market data via Finnhub
│   │   └── backtesting_service.py # Strategy backtesting logic
│   ├── utils/                     # Shared utilities
│   │   ├── config.py              # App configuration
│   │   ├── data_pipeline.py       # Data ETL helpers
│   │   └── wide_to_long_converter.py
│   ├── requirements.txt           # Python dependencies
│   └── .env                       # API keys (not committed)
│
├── frontend/                      # React / Vite dashboard
│   ├── src/
│   │   ├── App.jsx                # Root layout & state management
│   │   ├── components/
│   │   │   ├── Header.jsx         # Navigation header
│   │   │   ├── StockSelector.jsx  # Ticker search & timeframe controls
│   │   │   ├── CandlestickChart.jsx
│   │   │   ├── ForecastPanel.jsx  # Direction, confidence, expected move
│   │   │   ├── SentimentChart.jsx # 30-day sentiment time-series
│   │   │   ├── BacktestPanel.jsx  # KPI cards & equity curve
│   │   │   └── HeadlinesPanel.jsx # Scored news feed
│   │   ├── App.css
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── examples/                      # Screenshots & demo media
└── README.md
```

---

## � Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| **Python** | 3.10 + |
| **Node.js** | 18 + |
| **npm** | 9 + |

You will also need a free **[Finnhub API key](https://finnhub.io/register)** for live market data and news.

### 1 — Clone the repo

```bash
git clone https://github.com/deepsahu21/Quantara.git
cd Quantara
```

### 2 — Backend setup

```bash
# Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r backend/requirements.txt
```

Create a `.env` file inside `backend/`:

```env
FINNHUB_API_KEY=your_finnhub_api_key_here
```

Start the API server:

```bash
uvicorn backend.app:app --reload
```

The API will be live at **http://localhost:8000**.

### 3 — Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 📡 API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tickers` | List all available tickers |
| `GET` | `/api/prediction/{ticker}` | Full prediction payload (OHLCV, forecast, sentiment, headlines) |
| `GET` | `/api/backtest/{ticker}` | Backtest metrics & equity curve |
| `GET` | `/api/ohlcv/{ticker}?days=180` | Raw OHLCV candlestick data |
| `GET` | `/api/news/{ticker}?days=7` | Recent company headlines |
| `GET` | `/api/sentiment/{ticker}?days=30` | Daily sentiment time-series |
| `GET` | `/api/doctor?ticker=AAPL` | Diagnostics & contract validation |

### Example response — `/api/prediction/AAPL`

```jsonc
{
  "ticker": "AAPL",
  "direction": "bullish",
  "confidence_class": "Strong",
  "direction_probability": 0.87,
  "mu_pct": 0.0141,            // expected move (decimal)
  "ohlcv": [ /* ... */ ],
  "sentiment_series": [ /* 30 data points */ ],
  "headlines": [ /* up to 10 scored articles */ ]
}
```

---

## 🛠 Tech Stack

<table>
  <tr>
    <td><b>Frontend</b></td>
    <td>React 18, Vite 5, Recharts, Axios</td>
  </tr>
  <tr>
    <td><b>Backend</b></td>
    <td>FastAPI, Uvicorn, Python 3.10+</td>
  </tr>
  <tr>
    <td><b>ML / Data</b></td>
    <td>XGBoost, CatBoost, scikit-learn, yfinance</td>
  </tr>
  <tr>
    <td><b>Data Sources</b></td>
    <td>Finnhub API (news + market data), Yahoo Finance (OHLCV)</td>
  </tr>
</table>

---

## � Security

- API keys are loaded server-side from `.env` and **never** exposed to the frontend.
- All external API calls (Finnhub, yfinance) are proxied through the FastAPI backend.
- CORS is locked to `localhost` development origins.

---

## 🗺 Roadmap

- [x] Interactive candlestick chart with volume overlay
- [x] ML-based directional forecasting with confidence bands
- [x] Finnhub news integration with keyword sentiment scoring
- [x] Backtesting engine with KPI dashboard
- [ ] FinBERT transformer-based sentiment analysis
- [ ] Portfolio-level multi-ticker view
- [ ] User authentication & saved watchlists
- [ ] Cloud deployment (Docker + AWS)

---

## 📜 License

This project is for **educational and research purposes**.

---

## 👤 Author

**Deep Sahu**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/deepsahu1)
[![Portfolio](https://img.shields.io/badge/Portfolio-000?style=flat-square&logo=vercel&logoColor=white)](https://deepsahu.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/deepsahu21)

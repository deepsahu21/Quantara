<div align="center">

# Quantara

**AI-Driven Trading Analytics Platform**

</div>

Quantara is a full-stack trading analytics dashboard that pulls together real-time market data, financial news sentiment, and machine-learning forecasts into one place. Pick a ticker, and the platform shows you a candlestick chart, a next-day directional prediction with a confidence score, a rolling sentiment trend built from recent headlines, and a full backtest of how the strategy would have performed historically — all in a single view.

The backend is a FastAPI server that handles data fetching (Finnhub, yfinance), ML inference, and backtesting logic. The frontend is a React dashboard built with Vite that visualizes everything in real time. The whole thing is containerized with Docker and orchestrated with Kubernetes, so it can run locally or be deployed to any cloud provider.

![Quantara Dashboard](examples/dashboard_full.png)

---

## Features

- **Interactive Candlestick Chart** — Full OHLCV price chart with volume overlay and timeframe controls ranging from 1 day to 1 year
- **Forecast Panel** — Next-day directional prediction (bullish or bearish) with confidence band and expected move percentage
- **Sentiment Analysis** — 30-day rolling sentiment score computed from financial news headlines, visualized as a time-series chart
- **Backtesting Engine** — Historical strategy evaluation showing cumulative PnL, Sharpe ratio, max drawdown, CAGR, and a full equity curve
- **Live Headlines Feed** — Latest scored news articles for the selected ticker, pulled from Finnhub
- **Ticker Search** — Search and switch between all tracked equities instantly

---

## Screenshots

<table>
  <tr>
    <td width="50%">
      <img src="examples/chart_forecast.png" alt="Chart & Forecast" />
      <p align="center"><em>Candlestick chart with forecast panel and sentiment trend</em></p>
    </td>
    <td width="50%">
      <img src="examples/backtest_headlines.png" alt="Backtest & Headlines" />
      <p align="center"><em>Backtest metrics with equity curve and scored headlines</em></p>
    </td>
  </tr>
</table>

---

## Tech Stack

**Frontend:** React, Vite, Recharts, Axios, Nginx

**Backend:** Python, FastAPI, Uvicorn

**ML & Data:** XGBoost, CatBoost, scikit-learn, yfinance, Finnhub API

**DevOps:** Docker, Docker Compose, Kubernetes, Nginx

---

## Project Structure

```
Quantara/
├── backend/                         # FastAPI server
│   ├── app.py                       # API routes & request handling
│   ├── models/                      # ML model training & inference
│   │   ├── model.py                 # Primary forecasting model
│   │   ├── baseline_models.py       # Baseline comparisons
│   │   ├── evaluate.py              # Model evaluation
│   │   ├── feature_engineering.py   # Feature transforms
│   │   └── model_preprocesser.py    # Data preprocessing
│   ├── services/                    # Backend services
│   │   ├── prediction_service.py    # ML prediction orchestration
│   │   ├── yfinance_service.py      # OHLCV market data
│   │   ├── finnhub_service.py       # News & market data via Finnhub
│   │   └── backtesting_service.py   # Strategy backtesting
│   ├── utils/                       # Shared utilities
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                        # React dashboard
│   ├── src/
│   │   ├── App.jsx                  # Root layout & state
│   │   └── components/
│   │       ├── CandlestickChart.jsx
│   │       ├── ForecastPanel.jsx
│   │       ├── SentimentChart.jsx
│   │       ├── BacktestPanel.jsx
│   │       ├── HeadlinesPanel.jsx
│   │       ├── StockSelector.jsx
│   │       └── Header.jsx
│   ├── nginx.conf                   # Nginx reverse proxy config
│   ├── Dockerfile
│   └── package.json
│
├── k8s/                             # Kubernetes manifests
│   ├── namespace.yaml
│   ├── backend.yaml
│   ├── frontend.yaml
│   ├── secrets.yaml
│   └── ingress.yaml
│
├── docker-compose.yml
├── examples/                        # Screenshots & demo media
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A free [Finnhub API key](https://finnhub.io/register)

### Running locally (without Docker)

**Backend:**

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -r backend/requirements.txt
```

Create a `backend/.env` file:

```
FINNHUB_API_KEY=your_key_here
```

Start the server:

```bash
uvicorn backend.app:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Docker

Build and run everything with a single command:

```bash
docker-compose up --build
```

This spins up:
- **Backend** on `http://localhost:8000`
- **Frontend** on `http://localhost:80`

The frontend Nginx container reverse-proxies all `/api` requests to the backend container, so everything just works.

To stop:

```bash
docker-compose down
```

---

## Kubernetes

If you want to deploy to a cluster, all the manifests are in `k8s/`.

```bash
# Create the namespace
kubectl apply -f k8s/namespace.yaml

# Create the secret with your Finnhub key
kubectl create secret generic quantara-secrets \
  --namespace=quantara \
  --from-literal=FINNHUB_API_KEY=your_key_here

# Build and tag images (adjust registry as needed)
docker build -t quantara-backend:latest ./backend
docker build -t quantara-frontend:latest ./frontend

# Deploy
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# (Optional) Apply ingress if you have an ingress controller
kubectl apply -f k8s/ingress.yaml
```

The backend runs as a `ClusterIP` service (internal only), and the frontend runs as a `LoadBalancer` service on port 80. Both deployments run 2 replicas with health checks configured.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tickers` | List all available tickers |
| `GET` | `/api/prediction/{ticker}` | Full prediction (OHLCV, forecast, sentiment, headlines) |
| `GET` | `/api/backtest/{ticker}` | Backtest metrics and equity curve |
| `GET` | `/api/ohlcv/{ticker}?days=180` | Raw OHLCV candlestick data |
| `GET` | `/api/news/{ticker}?days=7` | Recent company news headlines |
| `GET` | `/api/sentiment/{ticker}?days=30` | Daily sentiment time-series |
| `GET` | `/api/doctor?ticker=AAPL` | Diagnostics and contract validation |

---

## Roadmap

- [x] Interactive candlestick chart with volume overlay
- [x] ML-based directional forecasting with confidence bands
- [x] Finnhub news integration with sentiment scoring
- [x] Backtesting engine with KPI dashboard and equity curve
- [x] Real-time headlines feed with sentiment scores
- [x] Ticker search across tracked equities
- [x] Containerized with Docker and Docker Compose
- [x] Kubernetes deployment manifests with health checks
- [ ] FinBERT transformer-based sentiment analysis
- [ ] Portfolio-level multi-ticker view

---

## License

This project is for educational and research purposes.

---

## Author

**Deep Sahu** — [LinkedIn](https://linkedin.com/in/deepsahu1) · [Portfolio](https://deepsahu.vercel.app) · [GitHub](https://github.com/deepsahu21)

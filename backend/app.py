"""
FastAPI Application for Quantara Dashboard
Artifact-based inference (production mode)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import logging
from datetime import datetime

from services.prediction_service import get_prediction_service
from services.yfinance_service import get_ohlcv_data
from services.finnhub_service import get_company_news

from utils.data_pipeline import TICKERS



# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quantara_api")

logger.info("🚀 Quantara API booting...")
logger.info("📊 OHLCV source: yfinance")
logger.info("📰 News source: Finnhub")


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(
    title="Quantara API",
    description="AI-Driven Trading Analytics API",
    version="1.0.0",
)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------
class PredictionResponse(BaseModel):
    ticker: str
    direction: str
    direction_score: float
    volatility: float
    direction_probability: float
    confidence_class: str
    feature_attribution: Dict
    sentiment_series: List
    ohlcv: List
    backtest_metrics: Dict
    headlines: List
    timestamp: str


# -------------------------------------------------------------------
# Confidence Logic (Quantara Standard)
# -------------------------------------------------------------------
def classify_confidence(mu: float, sigma: float, prob: float) -> str:
    if mu > 0 and (mu - sigma) > 0:
        return "Strong"
    if mu < 0 and (mu + sigma) < 0:
        return "Strong"
    if prob >= 0.75:
        return "Moderate"
    if prob >= 0.50:
        return "Low"
    return "Very Low"


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Quantara API",
        "timestamp": datetime.utcnow().isoformat(),
    }


# -------------------------------------------------------------------
# Prediction Endpoint
# -------------------------------------------------------------------
@app.get("/api/prediction/{ticker}", response_model=PredictionResponse)
async def get_prediction(ticker: str):
    try:
        ticker = ticker.upper()
        logger.info(f"📈 Prediction requested for {ticker}")

        service = get_prediction_service()
        raw = service.get_prediction(ticker=ticker)

        mu = raw["direction_score"]
        sigma = raw["volatility"]
        prob = raw["direction_probability"]

        raw["confidence_class"] = classify_confidence(mu, sigma, prob)
        raw["timestamp"] = datetime.utcnow().isoformat()

        return raw

    except Exception as e:
        logger.exception("❌ Prediction error")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prediction: {str(e)}",
        )


# -------------------------------------------------------------------
# Market Data
# -------------------------------------------------------------------
@app.get("/api/market/{ticker}")
async def get_market_data(ticker: str, days: int = 180):
    try:
        data = get_ohlcv_data(ticker.upper(), days=days)
        return {
            "ticker": ticker.upper(),
            "data": data,
            "count": len(data),
            "source": "yfinance",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# News
# -------------------------------------------------------------------
@app.get("/api/news/{ticker}")
async def get_news(ticker: str, days: int = 7):
    try:
        news = get_company_news(ticker.upper(), days=days)
        return {
            "ticker": ticker.upper(),
            "articles": news,
            "count": len(news),
            "source": "finnhub",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# Available Tickers (MODEL = SOURCE OF TRUTH)
# -------------------------------------------------------------------
@app.get("/api/tickers")
async def get_available_tickers():
    try:
        service = get_prediction_service()
        tickers = service.ticker_encoder.classes_.tolist()

        return {
            "universe": "S&P 100",
            "count": len(tickers),
            "tickers": tickers,
        }

    except Exception as e:
        logger.exception("❌ Ticker load error")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading tickers: {str(e)}",
        )
    
# -------------------------------------------------------------------
# all tickers
# -------------------------------------------------------------------

@app.get("/api/universe")
def get_ticker_universe():
    return {
        "tickers": TICKERS
    }



# -------------------------------------------------------------------
# Run
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

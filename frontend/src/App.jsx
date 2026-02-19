import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

import Header from './components/Header';
import StockSelector from './components/StockSelector';
import CandlestickChart from './components/CandlestickChart';
import ForecastPanel from './components/ForecastPanel';
import SentimentChart from './components/SentimentChart';
import BacktestPanel from './components/BacktestPanel';
import HeadlinesPanel from './components/HeadlinesPanel';

import './App.css';

const API_BASE_URL = '/api';

const TIMEFRAME_TO_DAYS = {
  '1D': 1,
  '1W': 5,
  '1M': 21,
  '3M': 63,
  '6M': 126,
  '1Y': 252
};

function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('6M');
  const [showVolume, setShowVolume] = useState(true);

  const [validTickers, setValidTickers] = useState([]);
  const [predictionData, setPredictionData] = useState(null);
  const [backtestData, setBacktestData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /* ---------------- Ticker universe ---------------- */
  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/tickers`)
      .then(res => setValidTickers(res.data.tickers))
      .catch(() => {});
  }, []);

  /* ---------------- Prediction ---------------- */
  const fetchPrediction = async (t) => {
    try {
      setError(null);
      setLoading(true);
      const { data } = await axios.get(`${API_BASE_URL}/prediction/${t}`);
      setPredictionData(data);
    } catch {
      setError('Failed to load prediction data.');
    } finally {
      setLoading(false);
    }
  };

  /* ---------------- Backtest ---------------- */
  const fetchBacktest = async (t) => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/backtest/${t}`);
      setBacktestData(data);
    } catch {
      setBacktestData(null);
    }
  };

  useEffect(() => {
    fetchPrediction(ticker);
    fetchBacktest(ticker);
  }, [ticker]);

  /* ---------------- Timeframe slicing ---------------- */
  const slicedOHLCV = useMemo(() => {
    if (!predictionData?.ohlcv) return [];
    const days = TIMEFRAME_TO_DAYS[timeframe];
    return predictionData.ohlcv.slice(-days);
  }, [predictionData, timeframe]);

  /* ---------------- Expected move ---------------- */
  const expectedMovePct =
    typeof predictionData?.mu_pct === 'number'
      ? predictionData.mu_pct * 100
      : typeof predictionData?.direction_score === 'number'
        ? predictionData.direction_score * 100
        : null;

  if (loading && !predictionData) {
    return <div className="loading-screen">Loading Quantara…</div>;
  }

  return (
    <div className="app">
      <Header onRefresh={() => fetchPrediction(ticker)} />

      <div className="dashboard-container">
        {/* ================= TOP ROW ================= */}
        <div className="dashboard-top">
          {/* LEFT */}
          <div className="dashboard-left-top">
            <StockSelector
              ticker={ticker}
              validTickers={validTickers}
              onTickerChange={setTicker}
              timeframe={timeframe}
              onTimeframeChange={setTimeframe}
              showVolume={showVolume}
              onVolumeToggle={setShowVolume}
            />

            <div className="main-chart-container">
              <CandlestickChart
                data={slicedOHLCV}
                showVolume={showVolume}
              />
            </div>
          </div>

          {/* RIGHT */}
          <div className="dashboard-right-top">
            <ForecastPanel
              direction={predictionData?.direction}
              confidenceClass={predictionData?.confidence_class}
              confidenceBand={predictionData?.direction_probability}
              expectedMovePct={expectedMovePct}
            />

            <SentimentChart
              data={predictionData?.sentiment_series || []}
              timeframe="30D"
            />
          </div>
        </div>

        {/* ================= BOTTOM ROW ================= */}
        {/* Backtest should be the one that stretches; Headlines stays narrower */}
        <div
          className="dashboard-bottom"
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr',
            gap: '16px'
          }}
        >
          {/* BACKTEST (combined metrics + chart inside BacktestPanel) */}
          <div className="dashboard-left-bottom" style={{ minWidth: 0 }}>
            <BacktestPanel backtest={backtestData} />
          </div>

          {/* HEADLINES */}
          <div className="dashboard-right-bottom" style={{ minWidth: 0 }}>
            <HeadlinesPanel headlines={predictionData?.headlines || []} />
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}

export default App;

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

import Header from './components/Header';
import StockSelector from './components/StockSelector';
import CandlestickChart from './components/CandlestickChart';
import ForecastPanel from './components/ForecastPanel';
import SentimentChart from './components/SentimentChart';
import BacktestPanel, { BacktestChart } from './components/BacktestPanel';
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

  const [predictionData, setPredictionData] = useState(null);
  const [backtestData, setBacktestData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPredictionData = async (t) => {
    try {
      setLoading(true);
      setError(null);
      const { data } = await axios.get(`${API_BASE_URL}/prediction/${t}`);
      setPredictionData(data);
    } catch (err) {
      console.error(err);
      setError('Failed to load prediction data.');
      setPredictionData(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchBacktestData = async (t) => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/backtest/${t}`);
      setBacktestData(data);
    } catch (err) {
      console.error(err);
      setBacktestData(null);
    }
  };

  useEffect(() => {
    fetchPredictionData(ticker);
    fetchBacktestData(ticker);
  }, [ticker]);

  const slicedOHLCV = useMemo(() => {
    if (!predictionData?.ohlcv) return [];
    const days = TIMEFRAME_TO_DAYS[timeframe];
    return days ? predictionData.ohlcv.slice(-days) : predictionData.ohlcv;
  }, [predictionData, timeframe]);

  if (loading && !predictionData) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="loading-spinner" />
          <div className="loading-text">Loading Quantara...</div>
        </div>
      </div>
    );
  }

  const muPct = predictionData?.mu_pct;
  const expectedMovePct =
    typeof muPct === 'number' ? (muPct * 100).toFixed(2) : null;

  return (
    <div className="app">
      <Header onRefresh={() => fetchPredictionData(ticker)} />

      <div className="dashboard-container">
        <div className="dashboard-top">
          <div className="dashboard-left-top">
            <StockSelector
              ticker={ticker}
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

          <div className="dashboard-right-top">
            {/* KEEP LEGACY PROP NAMES → prevents NaN */}
            <ForecastPanel
              direction={predictionData?.direction}
              directionScore={predictionData?.direction_score}
              confidenceClass={predictionData?.confidence_class}
              probability={predictionData?.direction_probability}
              volatility={predictionData?.volatility}
              expectedMovePct={expectedMovePct}
            />

            <SentimentChart
              data={predictionData?.sentiment_series || []}
              timeframe="30D"
            />
          </div>
        </div>

        <div className="dashboard-bottom">
          <div className="dashboard-left-bottom">
            {backtestData?.backtest_metrics && (
              <BacktestPanel metrics={backtestData.backtest_metrics} />
            )}
          </div>

          <div className="dashboard-center-bottom">
            <BacktestChart
              data={backtestData?.equity_curve || []}
            />
          </div>

          <div className="dashboard-right-bottom">
            <HeadlinesPanel
              headlines={predictionData?.headlines || []}
            />
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}

export default App;

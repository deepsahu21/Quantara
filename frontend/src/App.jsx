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

/**
 * Trading-day approximations for client-side slicing
 */
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 🔹 backend-driven ticker universe
  const [validTickers, setValidTickers] = useState([]);

  /**
   * Fetch ticker universe ONCE
   */
  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/universe`)
      .then(res => {
        setValidTickers(res.data.tickers || []);
      })
      .catch(err => {
        console.error('Failed to load ticker universe', err);
      });
  }, []);

  /**
   * Fetch prediction + fallback market/news data
   */
  const fetchPredictionData = async (selectedTicker) => {
    try {
      setLoading(true);
      setError(null);

      const predictionResponse = await axios.get(
        `${API_BASE_URL}/prediction/${selectedTicker}`
      );

      let prediction = predictionResponse.data;

      // Fallback OHLCV
      if (!prediction.ohlcv || prediction.ohlcv.length === 0) {
        const marketResponse = await axios.get(
          `${API_BASE_URL}/market/${selectedTicker}`,
          { params: { days: 180 } }
        );
        prediction.ohlcv = marketResponse.data.data || [];
      }

      // Fallback headlines
      if (!prediction.headlines || prediction.headlines.length === 0) {
        const newsResponse = await axios.get(
          `${API_BASE_URL}/news/${selectedTicker}`,
          { params: { days: 7 } }
        );

        prediction.headlines = (newsResponse.data.articles || []).map(a => ({
          text: a.text || a.headline || '',
          sentiment_score: a.sentiment_score || 0,
          date: a.date || new Date().toISOString().split('T')[0],
          source: a.source || '',
          url: a.url || ''
        }));
      }

      setPredictionData(prediction);
    } catch (err) {
      console.error(err);
      setError('Failed to load prediction data.');

      setPredictionData({
        ticker: selectedTicker,
        direction_score: 0,
        direction: 'bullish',
        confidence_band: 0.5,
        confidence_class: 'Low',
        feature_attribution: { historical: 0.7, sentiment: 0.3 },
        sentiment_series: [],
        ohlcv: [],
        backtest_metrics: null,
        headlines: []
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Fetch on ticker change ONLY
   */
  useEffect(() => {
    if (ticker) {
      fetchPredictionData(ticker);
    }
  }, [ticker]);

  /**
   * Client-side OHLCV slicing for timeframe buttons
   */
  const slicedOHLCV = useMemo(() => {
    if (!predictionData?.ohlcv) return [];

    const days = TIMEFRAME_TO_DAYS[timeframe];
    if (!days) return predictionData.ohlcv;

    return predictionData.ohlcv.slice(-days);
  }, [predictionData, timeframe]);

  /**
   * Only allow tickers from backend universe
   */
  const handleTickerChange = (newTicker) => {
    if (validTickers.includes(newTicker)) {
      setTicker(newTicker);
    }
  };

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

  return (
    <div className="app">
      <Header onRefresh={() => fetchPredictionData(ticker)} />

      <div className="dashboard-container">
        <div className="dashboard-top">
          <div className="dashboard-left-top">
            <StockSelector
              ticker={ticker}
              validTickers={validTickers}
              onTickerChange={handleTickerChange}
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
            <ForecastPanel
              directionScore={predictionData?.direction_score || 0}
              direction={predictionData?.direction || 'bullish'}
              confidenceBand={predictionData?.confidence_band || 0.5}
              confidenceClass={predictionData?.confidence_class || 'Low'}
            />

            <SentimentChart
              data={predictionData?.sentiment_series || []}
              timeframe="7D"
            />
          </div>
        </div>

        <div className="dashboard-bottom">
          <div className="dashboard-left-bottom">
            <BacktestPanel
              metrics={predictionData?.backtest_metrics}
              chartData={[]}
            />
          </div>

          <div className="dashboard-center-bottom">
            <BacktestChart data={[]} />
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

import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './BacktestPanel.css';

const BacktestPanel = ({ metrics, chartData }) => {
  const [activeTab, setActiveTab] = useState('AI Strategy');

  if (!metrics) {
    return (
      <div className="backtest-panel">
        <div className="panel-header">
          <span className="panel-title">Backtest</span>
        </div>
        <div className="loading-placeholder">Loading backtest data...</div>
      </div>
    );
  }

  return (
    <div className="backtest-panel">
      <div className="panel-header">
        <span className="panel-title">Backtest</span>
        <div className="backtest-tabs">
          <button
            className={`tab-btn ${activeTab === 'AI Strategy' ? 'active' : ''}`}
            onClick={() => setActiveTab('AI Strategy')}
          >
            AI Strategy
          </button>
          <button
            className={`tab-btn ${activeTab === 'SMA 20/30' ? 'active' : ''}`}
            onClick={() => setActiveTab('SMA 20/30')}
          >
            SMA 20/30
          </button>
        </div>
      </div>

      {activeTab === 'AI Strategy' ? (
        <div className="backtest-metrics">
          <div className="metric-row">
            <span className="metric-label">Cumulative P&L</span>
            <span className="metric-value">
              {metrics.cumulative_pnl > 0 ? '+' : ''}{metrics.cumulative_pnl?.toFixed(2) || 'N/A'}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Sharpe</span>
            <span className="metric-value">
              {metrics.sharpe?.toFixed(2) || 'N/A'}
              {metrics.sharpe_change && (
                <span className={`metric-change ${metrics.sharpe_change > 0 ? 'positive' : 'negative'}`}>
                  {metrics.sharpe_change > 0 ? '+' : ''}{metrics.sharpe_change.toFixed(1)}%
                </span>
              )}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Max Drawdown</span>
            <span className="metric-value">
              {metrics.max_drawdown > 0 ? '+' : ''}{metrics.max_drawdown?.toFixed(1) || 'N/A'}
              <span className="metric-pct">({metrics.max_drawdown_pct?.toFixed(1) || 0}%)</span>
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">CAGR</span>
            <span className="metric-value">{metrics.cagr?.toFixed(1) || 'N/A'}</span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Trades</span>
            <span className="metric-value">{metrics.trades || 'N/A'}</span>
          </div>
        </div>
      ) : (
        <div className="sma-metrics">
          <div className="metric-note">
            SMA 20/30 strategy backtest metrics
          </div>
        </div>
      )}

      <div className="backtest-note">
        Historical simulation performance. Past performance does not guarantee future results.
      </div>
    </div>
  );
};

export const BacktestChart = ({ data }) => {
  const chartData = React.useMemo(() => {
    if (!data || !Array.isArray(data)) {
      // Generate mock data if none provided
      return Array.from({ length: 30 }, (_, i) => ({
        date: `Day ${i + 1}`,
        value: Math.random() * 100 + 1000
      }));
    }
    return data;
  }, [data]);

  return (
    <div className="backtest-chart-panel">
      <div className="panel-header">
        <span className="panel-title">Backtest</span>
        <span className="chart-change positive">▲0.30%</span>
      </div>
      <div className="backtest-chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.3} />
            <XAxis
              dataKey="date"
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
            />
            <YAxis
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-primary)'
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--accent-blue)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-footer">
        <div className="chart-sources">Sources: Postgres, yfinance, RSS</div>
        <div className="chart-status">Status: updated just now</div>
      </div>
    </div>
  );
};

export default BacktestPanel;


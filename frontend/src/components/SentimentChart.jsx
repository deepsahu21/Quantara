import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import './SentimentChart.css';

const DAY_MS = 24 * 60 * 60 * 1000;

const SentimentChart = ({ data, timeframe = '7D' }) => {
  const [activeTab, setActiveTab] = useState(timeframe);

  const chartData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];

    // Normalize each point to have a numeric x (unix ms)
    const normalized = data
      .map((item) => {
        // Prefer backend-provided x (unix ms)
        let x =
          typeof item.x === 'number' && item.x > 0
            ? item.x
            : typeof item.timestamp === 'number' && item.timestamp > 0
              ? item.timestamp * 1000
              : null;

        // Fallback: parse date string if possible
        if (!x && typeof item.date === 'string') {
          const parsed = Date.parse(item.date); // works for ISO
          if (!Number.isNaN(parsed)) x = parsed;
        }

        if (!x) return null;

        // Support either value or score
        const vRaw =
          typeof item.value === 'number'
            ? item.value
            : typeof item.score === 'number'
              ? item.score
              : null;

        const value = typeof vRaw === 'number' ? vRaw : 0;

        // Tooltip label: prefer a readable ISO-ish string
        const label =
          typeof item.date === 'string' && item.date
            ? item.date
            : new Date(x).toISOString().slice(0, 10);

        return { x, value, label };
      })
      .filter(Boolean)
      .sort((a, b) => a.x - b.x); // oldest -> newest

    if (normalized.length === 0) return [];

    // Filter by time window (7D / 30D), not by last N points
    const now = normalized[normalized.length - 1].x;
    const windowMs = activeTab === '7D' ? 7 * DAY_MS : 30 * DAY_MS;
    const cutoff = now - windowMs;

    return normalized.filter((p) => p.x >= cutoff);
  }, [data, activeTab]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload;

      // label here is x (because XAxis uses dataKey="x")
      const dt = typeof label === 'number' ? new Date(label) : null;
      const nice =
        dt ? dt.toISOString().slice(0, 16).replace('T', ' ') : point.label;

      return (
        <div className="sentiment-tooltip">
          <div className="tooltip-label">{nice}</div>
          <div className="tooltip-value">
            Sentiment: {point.value > 0 ? '+' : ''}{Number(point.value).toFixed(3)}
          </div>
        </div>
      );
    }
    return null;
  };

  // Compact ticks like 12/30
  const tickFormatter = (x) => {
    const d = new Date(x);
    return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
  };

  return (
    <div className="sentiment-panel">
      <div className="panel-header">
        <span className="panel-title">Sentiment</span>
        <div className="sentiment-tabs">
          <button
            className={`tab-btn ${activeTab === '7D' ? 'active' : ''}`}
            onClick={() => setActiveTab('7D')}
          >
            7D
          </button>
          <button
            className={`tab-btn ${activeTab === '30D' ? 'active' : ''}`}
            onClick={() => setActiveTab('30D')}
          >
            30D
          </button>
        </div>
      </div>

      <div className="sentiment-chart-container">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.3} />
              <XAxis
                dataKey="x"
                type="number"
                domain={['dataMin', 'dataMax']}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                tickFormatter={tickFormatter}
              />
              <YAxis
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                domain={[-1, 1]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--accent-blue)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: 'var(--accent-teal)' }}
              />
              <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="2 2" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-placeholder">
            {Array.isArray(data) && data.length === 0
              ? 'No sentiment data available'
              : 'Loading sentiment data...'}
          </div>
        )}
      </div>
    </div>
  );
};

export default SentimentChart;

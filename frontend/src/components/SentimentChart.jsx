import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import './SentimentChart.css';

const SentimentChart = ({ data, timeframe = '7D' }) => {
  const [activeTab, setActiveTab] = useState(timeframe);

  const chartData = React.useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    
    // Filter based on active tab
    const days = activeTab === '7D' ? 7 : 30;
    return data.slice(-days).map(item => ({
      date: item.date,
      value: item.value,
      label: item.label || item.date
    }));
  }, [data, activeTab]);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="sentiment-tooltip">
          <div className="tooltip-label">{data.label}</div>
          <div className="tooltip-value">
            Sentiment: {data.value > 0 ? '+' : ''}{data.value.toFixed(3)}
          </div>
        </div>
      );
    }
    return null;
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
                dataKey="label"
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                tickFormatter={(value) => {
                  if (typeof value === 'string' && value.includes('Day')) {
                    return value.replace(' Day', 'D');
                  }
                  return value;
                }}
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
            {data && data.length === 0 
              ? 'No sentiment data available' 
              : 'Loading sentiment data...'}
          </div>
        )}
      </div>
    </div>
  );
};

export default SentimentChart;


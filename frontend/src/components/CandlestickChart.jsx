import React, { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import './CandlestickChart.css';

const CandlestickChart = ({ data, showVolume = true }) => {
  const chartData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    
    return data.map((item, index) => ({
      date: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
      sma60: item.sma60,
      sma90: item.sma90,
      index
    }));
  }, [data]);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <div className="tooltip-date">{data.date}</div>
          <div className="tooltip-row">
            <span>Open:</span>
            <span>{data.open.toFixed(2)}</span>
          </div>
          <div className="tooltip-row">
            <span>High:</span>
            <span>{data.high.toFixed(2)}</span>
          </div>
          <div className="tooltip-row">
            <span>Low:</span>
            <span>{data.low.toFixed(2)}</span>
          </div>
          <div className="tooltip-row">
            <span>Close:</span>
            <span>{data.close.toFixed(2)}</span>
          </div>
          <div className="tooltip-row">
            <span>SMA60:</span>
            <span className={data.close > data.sma60 ? 'positive' : 'negative'}>
              {data.close > data.sma60 ? '+' : ''}{(data.close - data.sma60).toFixed(3)}
            </span>
          </div>
          <div className="tooltip-row">
            <span>SMA90:</span>
            <span>{data.sma90.toFixed(2)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  if (!chartData.length) {
    return (
      <div className="chart-container">
        <div className="chart-placeholder">
          {data && data.length === 0 
            ? 'No market data available. Please check your API connection.' 
            : 'Loading chart data...'}
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.3} />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            yAxisId="price"
            orientation="right"
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            domain={['auto', 'auto']}
          />
          {showVolume && (
            <YAxis
              yAxisId="volume"
              orientation="right"
              tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
              domain={[0, 'auto']}
              hide
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          
          {/* Volume bars */}
          {showVolume && (
            <Bar
              yAxisId="volume"
              dataKey="volume"
              fill="var(--text-muted)"
              opacity={0.3}
            />
          )}
          
          {/* SMA lines */}
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="sma60"
            stroke="var(--accent-blue)"
            strokeWidth={2}
            dot={false}
            name="SMA60"
          />
          
          {/* Price line (simplified - full candlestick requires custom component) */}
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="close"
            stroke="var(--accent-teal)"
            strokeWidth={2}
            dot={false}
            name="Close"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CandlestickChart;


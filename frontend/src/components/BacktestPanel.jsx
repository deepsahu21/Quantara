import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import './BacktestPanel.css';

/* ---------------- Helpers ---------------- */

const RANGE_TO_BARS = {
  '1M': 21,
  '3M': 63,
  '6M': 126,
  '1Y': 252,
  '5Y': 1260,
  'All time': null
};

function toDate(value) {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function normalizeEquityPoint(p) {
  if (!p || typeof p !== 'object') return null;

  const date =
    p.date ?? p.time ?? p.timestamp ?? p.datetime ?? p.t ?? p.ds ?? p.x;

  const value =
    p.value ??
    p.equity ??
    p.equity_curve ??
    p.portfolio_value ??
    p.nav ??
    p.y;

  const d = toDate(date);
  const v = typeof value === 'number' ? value : Number(value);

  if (!d || !Number.isFinite(v)) return null;

  // keep a string key recharts can show
  const iso = d.toISOString().slice(0, 10);
  return { date: iso, _date: d, value: v };
}

function normalizeEquityCurve(raw) {
  if (!Array.isArray(raw)) return [];
  const pts = raw
    .map(normalizeEquityPoint)
    .filter(Boolean)
    .sort((a, b) => a._date - b._date);

  // remove internal Date so recharts doesn't serialize weirdly
  return pts.map(({ _date, ...rest }) => rest);
}

function sliceByRange(curve, rangeKey) {
  if (!Array.isArray(curve) || curve.length === 0) return [];
  const bars = RANGE_TO_BARS[rangeKey];
  if (!bars) return curve;
  return curve.slice(-bars);
}

function safeStd(values) {
  if (!values.length) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance =
    values.reduce((acc, v) => acc + (v - mean) * (v - mean), 0) / values.length;
  return Math.sqrt(variance);
}

function computeMetricsFromEquityCurve(curve) {
  // curve: [{date, value}] sorted asc
  if (!curve || curve.length < 2) {
    return {
      cumulative_pnl_pct: null,
      sharpe: null,
      max_drawdown_pct: null,
      cagr_pct: null
    };
  }

  const start = curve[0].value;
  const end = curve[curve.length - 1].value;

  if (!Number.isFinite(start) || !Number.isFinite(end) || start <= 0) {
    return {
      cumulative_pnl_pct: null,
      sharpe: null,
      max_drawdown_pct: null,
      cagr_pct: null
    };
  }

  // daily-ish returns based on adjacent points
  const rets = [];
  for (let i = 1; i < curve.length; i++) {
    const prev = curve[i - 1].value;
    const cur = curve[i].value;
    if (prev > 0 && Number.isFinite(prev) && Number.isFinite(cur)) {
      rets.push(cur / prev - 1);
    }
  }

  const mean = rets.length ? rets.reduce((a, b) => a + b, 0) / rets.length : 0;
  const std = safeStd(rets);

  const sharpe =
    std > 1e-12 ? (Math.sqrt(252) * mean) / std : null;

  // max drawdown
  let peak = curve[0].value;
  let maxDD = 0; // negative number
  for (let i = 1; i < curve.length; i++) {
    const v = curve[i].value;
    if (v > peak) peak = v;
    const dd = peak > 0 ? v / peak - 1 : 0;
    if (dd < maxDD) maxDD = dd;
  }

  const cumulative = end / start - 1;

  // CAGR approximated with trading days
  const n = curve.length - 1;
  const years = n / 252;
  const cagr =
    years > 0 ? Math.pow(end / start, 1 / years) - 1 : null;

  return {
    cumulative_pnl_pct: cumulative * 100,
    sharpe,
    max_drawdown_pct: maxDD * 100,
    cagr_pct: cagr != null ? cagr * 100 : null
  };
}

function normalizeSide(s) {
  if (s == null) return null;
  const x = String(s).toLowerCase();
  if (x.includes('buy') || x === 'b') return 'BUY';
  if (x.includes('sell') || x === 's') return 'SELL';
  return null;
}

function countTransactionsFromTradeLog(trades, startDateStr, endDateStr) {
  if (!Array.isArray(trades) || trades.length === 0) return null;

  const start = toDate(startDateStr);
  const end = toDate(endDateStr);

  let count = 0;
  for (const t of trades) {
    if (!t || typeof t !== 'object') continue;

    const ts =
      t.date ?? t.time ?? t.timestamp ?? t.datetime ?? t.t ?? t.executed_at;

    const d = toDate(ts);
    if (!d) continue;
    if (start && d < start) continue;
    if (end && d > end) continue;

    // count BUY/SELL actions as transactions
    const side = normalizeSide(t.side ?? t.action ?? t.type ?? t.order_side);
    if (side) count += 1;
  }

  return Number.isFinite(count) ? count : null;
}

function mapPositionValue(v) {
  if (v == null) return 0;
  if (typeof v === 'number' && Number.isFinite(v)) return v;

  const s = String(v).toLowerCase();
  if (s.includes('long')) return 1;
  if (s.includes('short')) return -1;
  if (s.includes('flat') || s.includes('cash') || s.includes('none')) return 0;

  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function countTransactionsFromPositions(positions) {
  if (!Array.isArray(positions) || positions.length < 2) return null;

  let count = 0;
  let prev = mapPositionValue(positions[0]);

  for (let i = 1; i < positions.length; i++) {
    const cur = mapPositionValue(positions[i]);
    if (cur === prev) continue;

    // 0->1 or 1->0 => 1 transaction
    // -1->1 or 1->-1 => 2 transactions
    const diff = Math.abs(cur - prev);
    count += diff >= 2 ? 2 : 1;

    prev = cur;
  }

  return count;
}

function fmtPct(v, digits = 2) {
  if (v == null || !Number.isFinite(v)) return 'N/A';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(digits)}%`;
}

function fmtNum(v, digits = 2) {
  if (v == null || !Number.isFinite(v)) return 'N/A';
  return v.toFixed(digits);
}

/* ---------------- Component ---------------- */

const BacktestPanel = ({ backtest, metrics, chartData }) => {
  const [activeTab, setActiveTab] = useState('AI Strategy');
  const [activeRange, setActiveRange] = useState('1Y');

  // Try to support multiple backend shapes:
  // - backtest.equity_curve
  // - backtest.strategies.ai.equity_curve
  // - backtest.ai_strategy.equity_curve
  // - chartData passed directly
  const strategyData = useMemo(() => {
    const bt = backtest ?? null;

    // strategies map shape
    const strategies = bt?.strategies;
    if (strategies && typeof strategies === 'object') {
      if (activeTab === 'AI Strategy') {
        return (
          strategies.ai ??
          strategies.ai_strategy ??
          strategies.model ??
          strategies.primary ??
          bt
        );
      }
      return (
        strategies.sma ??
        strategies.sma_20_30 ??
        strategies['SMA 20/30'] ??
        bt?.sma_20_30 ??
        bt
      );
    }

    // flat keys shape
    if (activeTab === 'SMA 20/30') {
      return bt?.sma_20_30 ?? bt?.sma ?? bt;
    }

    return bt;
  }, [backtest, activeTab]);

  const equityCurve = useMemo(() => {
    const raw =
      strategyData?.equity_curve ??
      strategyData?.equity ??
      strategyData?.curve ??
      backtest?.equity_curve ??
      chartData ??
      [];
    return normalizeEquityCurve(raw);
  }, [strategyData, backtest, chartData]);

  const slicedCurve = useMemo(() => {
    return sliceByRange(equityCurve, activeRange);
  }, [equityCurve, activeRange]);

  const computed = useMemo(() => {
    const m = computeMetricsFromEquityCurve(slicedCurve);
    return m;
  }, [slicedCurve]);

  const tradesCount = useMemo(() => {
    // Prefer explicit trade logs if they exist
    const tradeLog =
      strategyData?.trades ??
      strategyData?.transactions ??
      strategyData?.trade_log ??
      backtest?.trades ??
      backtest?.transactions ??
      backtest?.trade_log ??
      null;

    const startDate = slicedCurve?.[0]?.date;
    const endDate = slicedCurve?.[slicedCurve.length - 1]?.date;

    const fromLog = countTransactionsFromTradeLog(tradeLog, startDate, endDate);
    if (fromLog != null) return fromLog;

    // Fallback: derive from positions/signals
    const posSeries =
      strategyData?.positions ??
      strategyData?.position_series ??
      strategyData?.signals ??
      strategyData?.signal_series ??
      backtest?.positions ??
      backtest?.signals ??
      null;

    // If positions are aligned with full curve length, slice them the same way
    if (Array.isArray(posSeries) && equityCurve.length > 0) {
      const bars = RANGE_TO_BARS[activeRange];
      const slicedPos = bars ? posSeries.slice(-bars) : posSeries;
      const fromPos = countTransactionsFromPositions(slicedPos);
      if (fromPos != null) return fromPos;
    }

    // Last fallback: if backend provides a number, show it
    const provided =
      strategyData?.backtest_metrics?.trades ??
      backtest?.backtest_metrics?.trades ??
      metrics?.trades ??
      null;

    return provided ?? 0;
  }, [strategyData, backtest, metrics, slicedCurve, equityCurve.length, activeRange]);

  const mergedMetrics = useMemo(() => {
    // Use computed metrics (timeframe-consistent).
    // Keep backend values only if computed is missing.
    const base = strategyData?.backtest_metrics ?? backtest?.backtest_metrics ?? metrics ?? {};

    const cumulative = computed.cumulative_pnl_pct ?? base.cumulative_pnl ?? base.cumulative_pnl_pct ?? null;
    const sharpe = computed.sharpe ?? base.sharpe ?? null;
    const maxDD = computed.max_drawdown_pct ?? base.max_drawdown_pct ?? base.max_drawdown ?? null;
    const cagr = computed.cagr_pct ?? base.cagr ?? base.cagr_pct ?? null;

    return {
      cumulative_pnl_pct: typeof cumulative === 'number' ? cumulative : null,
      sharpe: typeof sharpe === 'number' ? sharpe : null,
      max_drawdown_pct: typeof maxDD === 'number' ? maxDD : null,
      cagr_pct: typeof cagr === 'number' ? cagr : null,
      trades: tradesCount
    };
  }, [computed, strategyData, backtest, metrics, tradesCount]);

  const chartChange = useMemo(() => {
    if (!slicedCurve || slicedCurve.length < 2) return null;
    const start = slicedCurve[0].value;
    const end = slicedCurve[slicedCurve.length - 1].value;
    if (!Number.isFinite(start) || !Number.isFinite(end) || start <= 0) return null;
    return (end / start - 1) * 100;
  }, [slicedCurve]);

  const isPositive = typeof chartChange === 'number' ? chartChange >= 0 : true;

  if (!backtest && !metrics && (!chartData || chartData.length === 0)) {
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
      {/* HEADER (title + strategy tabs) */}
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

      {/* RANGE TABS (affects BOTH metrics + chart) */}
      <div className="chart-tabs" style={{ marginTop: '8px' }}>
        {['1M', '3M', '6M', '1Y', '5Y', 'All time'].map(r => (
          <button
            key={r}
            className={`timeframe-btn ${activeRange === r ? 'active' : ''}`}
            onClick={() => setActiveRange(r)}
            type="button"
          >
            {r}
          </button>
        ))}
      </div>

      {/* METRICS */}
      {activeTab === 'AI Strategy' ? (
        <div className="backtest-metrics" style={{ marginTop: '10px' }}>
          <div className="metric-row">
            <span className="metric-label">Cumulative P&amp;L</span>
            <span className="metric-value">
              {fmtPct(mergedMetrics.cumulative_pnl_pct, 2)}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Sharpe</span>
            <span className="metric-value">{fmtNum(mergedMetrics.sharpe, 2)}</span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Max Drawdown</span>
            <span className="metric-value">
              {fmtPct(mergedMetrics.max_drawdown_pct, 2)}
              {mergedMetrics.max_drawdown_pct != null && Number.isFinite(mergedMetrics.max_drawdown_pct) && (
                <span className="metric-pct">({Math.abs(mergedMetrics.max_drawdown_pct).toFixed(2)}%)</span>
              )}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">CAGR</span>
            <span className="metric-value">{fmtPct(mergedMetrics.cagr_pct, 2)}</span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Trades</span>
            <span className="metric-value">{Number.isFinite(mergedMetrics.trades) ? mergedMetrics.trades : 'N/A'}</span>
          </div>
        </div>
      ) : (
        <div className="sma-metrics" style={{ marginTop: '10px' }}>
          <div className="metric-note">SMA 20/30 strategy backtest metrics</div>
        </div>
      )}

      {/* CHART */}
      <div className="backtest-chart-panel" style={{ marginTop: '18px' }}>
        <div className="panel-header">
          <span className="panel-title">Backtest</span>
          <span className={`chart-change ${isPositive ? 'positive' : 'negative'}`}>
            {chartChange == null ? '—' : (isPositive ? '▲' : '▼')}{chartChange == null ? '' : Math.abs(chartChange).toFixed(2)}%
          </span>
        </div>

        <div className="backtest-chart-container">
          {(!slicedCurve || slicedCurve.length === 0) ? (
            <div className="chart-placeholder">No backtest data available.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={slicedCurve} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                />
                {/* FORCE Y-AXIS ON LEFT */}
                <YAxis
                  orientation="left"
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
          )}
        </div>

        <div className="chart-footer">
          <div className="chart-sources">Sources: Postgres, yfinance, RSS</div>
          <div className="chart-status">Status: updated just now</div>
        </div>
      </div>

      <div className="backtest-note">
        Historical simulation performance. Past performance does not guarantee future results.
      </div>
    </div>
  );
};

export default BacktestPanel;


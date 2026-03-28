/**
 * Static demo snapshot: AAPL as of 2024-11-12 (NYSE session).
 * OHLC for that session is aligned to public daily figures; history is synthetic.
 */

export const MOCK_AS_OF_DATE = '2024-11-12';

const LAST_BAR = {
  open: 224.64,
  high: 225.35,
  low: 222.76,
  close: 224.31,
  volume: 52_300_000
};

function tradingDatesDescending(endYmd, count) {
  const out = [];
  const cur = new Date(`${endYmd}T12:00:00Z`);
  while (out.length < count) {
    const dow = cur.getUTCDay();
    if (dow !== 0 && dow !== 6) {
      out.push(cur.toISOString().slice(0, 10));
    }
    cur.setUTCDate(cur.getUTCDate() - 1);
  }
  return out.reverse();
}

function buildOhlcv() {
  const N = 290;
  const dates = tradingDatesDescending(MOCK_AS_OF_DATE, N);
  const closes = [];
  let c = 178.5;
  for (let i = 0; i < N; i++) {
    const drift = 0.00035;
    const noise = Math.sin(i * 0.085) * 0.014 + Math.cos(i * 0.29) * 0.006;
    c *= 1 + drift + noise;
    closes.push(c);
  }
  const scale = LAST_BAR.close / closes[N - 1];
  for (let i = 0; i < N; i++) closes[i] *= scale;

  const rows = dates.map((date, i) => {
    const cl = closes[i];
    const op = i === 0 ? cl : closes[i - 1];
    const hi = Math.max(op, cl) * (1 + Math.abs(Math.sin(i * 0.9)) * 0.007);
    const lo = Math.min(op, cl) * (1 - Math.abs(Math.cos(i * 0.7)) * 0.007);
    const vol = 42_000_000 + Math.floor(Math.sin(i * 2.07) * 11_000_000);
    const ts = Math.floor(Date.parse(`${date}T21:00:00Z`) / 1000);
    return {
      date,
      open: op,
      high: hi,
      low: lo,
      close: cl,
      volume: Math.max(10_000_000, vol),
      sma60: 0,
      sma90: 0,
      timestamp: ts
    };
  });

  const last = rows[N - 1];
  Object.assign(last, LAST_BAR);

  for (let i = 0; i < N; i++) {
    const from = Math.max(0, i - 59);
    const slice60 = rows.slice(from, i + 1);
    const from90 = Math.max(0, i - 89);
    const slice90 = rows.slice(from90, i + 1);
    const sma60 =
      slice60.reduce((s, r) => s + r.close, 0) / slice60.length;
    const sma90 =
      slice90.reduce((s, r) => s + r.close, 0) / slice90.length;
    rows[i].sma60 = Math.round(sma60 * 100) / 100;
    rows[i].sma90 = Math.round(sma90 * 100) / 100;
  }

  return rows;
}

function calendarDaysEnding(endYmd, nDays) {
  const end = new Date(`${endYmd}T12:00:00Z`);
  const days = [];
  for (let i = nDays - 1; i >= 0; i--) {
    const d = new Date(end);
    d.setUTCDate(d.getUTCDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  return days;
}

function buildSentimentSeries() {
  const days = calendarDaysEnding(MOCK_AS_OF_DATE, 30);
  let v = 0.12;
  return days.map((date, i) => {
    v += Math.sin(i * 0.45) * 0.04;
    v = Math.max(-0.85, Math.min(0.85, v));
    const x = Date.parse(`${date}T12:00:00Z`);
    return { date, x, value: Math.round(v * 1000) / 1000 };
  });
}

function buildMockHeadlines() {
  return [
    {
      headline:
        'Apple suppliers report steady iPhone build plans heading into holidays',
      title:
        'Apple suppliers report steady iPhone build plans heading into holidays',
      text: 'Apple suppliers report steady iPhone build plans heading into holidays',
      sentiment_score: 0.42,
      date: MOCK_AS_OF_DATE,
      timestamp: 1731427200
    },
    {
      headline: 'Analysts trim near-term estimates after mixed supplier data',
      title: 'Analysts trim near-term estimates after mixed supplier data',
      text: 'Analysts trim near-term estimates after mixed supplier data',
      sentiment_score: -0.18,
      date: '2024-11-11',
      timestamp: 1731340800
    },
    {
      headline: 'Apple services growth remains focus ahead of year-end quarter',
      title: 'Apple services growth remains focus ahead of year-end quarter',
      text: 'Apple services growth remains focus ahead of year-end quarter',
      sentiment_score: 0.28,
      date: '2024-11-11',
      timestamp: 1731351600
    },
    {
      headline: 'Regulatory scrutiny on App Store rules continues in key regions',
      title: 'Regulatory scrutiny on App Store rules continues in key regions',
      text: 'Regulatory scrutiny on App Store rules continues in key regions',
      sentiment_score: -0.35,
      date: '2024-11-10',
      timestamp: 1731254400
    },
    {
      headline:
        'Institutional filings show modest increase in Apple exposure in Q3',
      title:
        'Institutional filings show modest increase in Apple exposure in Q3',
      text:
        'Institutional filings show modest increase in Apple exposure in Q3',
      sentiment_score: 0.22,
      date: '2024-11-09',
      timestamp: 1731139200
    }
  ];
}

function buildEquityCurve() {
  const dates = tradingDatesDescending(MOCK_AS_OF_DATE, 260);
  let v = 100;
  const curve = dates.map((date, i) => {
    v *= 1 + Math.sin(i * 0.031) * 0.006 + 0.00025;
    return { date, value: Math.round(v * 10000) / 10000 };
  });
  curve[curve.length - 1].value = curve[curve.length - 2].value * 1.002;
  return curve;
}

export const MOCK_PREDICTION = {
  ticker: 'AAPL',
  as_of: MOCK_AS_OF_DATE,
  ohlcv: buildOhlcv(),
  direction: 'bullish',
  confidence_class: 'Moderate',
  direction_probability: 0.63,
  mu_pct: 0.0092,
  sentiment_series: buildSentimentSeries(),
  headlines: buildMockHeadlines()
};

export const MOCK_BACKTEST = {
  backtest_metrics: {
    cumulative_pnl_pct: 21.4,
    sharpe: 1.12,
    max_drawdown_pct: -14.2,
    cagr_pct: 16.8,
    trades: 42
  },
  equity_curve: buildEquityCurve()
};

import React, { useEffect, useMemo, useRef, useState } from 'react';
import './StockSelector.css';

const StockSelector = ({
  ticker = '',
  validTickers = [],
  onTickerChange,
  timeframe,
  onTimeframeChange,
  showVolume,
  onVolumeToggle
}) => {
  const timeframes = ['1D', '1W', '1M', '3M', '6M', '1Y'];

  const containerRef = useRef(null);
  const dropdownRef = useRef(null);

  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  /* Sync input only after commit */
  useEffect(() => {
    if (!open) setQuery(ticker || '');
  }, [ticker, open]);

  /* -------------------------------------------------- */
  /* PROPER AUTOCOMPLETE (PREFIX + CONTAINS FALLBACK)   */
  /* -------------------------------------------------- */
  const filteredTickers = useMemo(() => {
    if (!Array.isArray(validTickers)) return [];

    const q = query.trim().toUpperCase();

    // Empty → ALL tickers
    if (!q) return validTickers;

    const startsWith = [];
    const contains = [];

    for (const t of validTickers) {
      const upper = t.toUpperCase();
      if (upper.startsWith(q)) {
        startsWith.push(t);
      } else if (upper.includes(q)) {
        contains.push(t);
      }
    }

    return [...startsWith, ...contains];
  }, [query, validTickers]);

  /* Reset scroll only when query changes or open */
  useEffect(() => {
    if (open && dropdownRef.current) {
      dropdownRef.current.scrollTop = 0;
    }
  }, [open, query]);

  /* Close on outside click */
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
        setActiveIndex(0);
        setQuery(ticker || '');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [ticker]);

  const commitSelection = (t) => {
    setQuery(t);
    setOpen(false);
    setActiveIndex(0);
    onTickerChange?.(t);
  };

  const handleKeyDown = (e) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) {
      setOpen(true);
      setActiveIndex(0);
      return;
    }

    if (e.key === 'Escape') {
      setOpen(false);
      setQuery(ticker || '');
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, filteredTickers.length - 1));
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, 0));
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      const t = filteredTickers[activeIndex];
      if (t) commitSelection(t);
    }
  };

  return (
    <div className="stock-selector" ref={containerRef}>
      <div className="selector-left">
        <div className="ticker-combobox">
          <input
            className="ticker-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value.toUpperCase());
              setOpen(true);
              setActiveIndex(0);
            }}
            onFocus={() => {
              setOpen(true);
              setActiveIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Select ticker"
            spellCheck={false}
          />

          {open && (
            <div
              ref={dropdownRef}
              className="ticker-dropdown"
              style={{
                maxHeight: '240px',
                overflowY: 'auto'
              }}
            >
              {filteredTickers.map((t, idx) => (
                <div
                  key={t}
                  className={`ticker-option ${
                    idx === activeIndex ? 'active' : ''
                  } ${t === ticker ? 'selected' : ''}`}
                  onMouseEnter={() => setActiveIndex(idx)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    commitSelection(t);
                  }}
                >
                  {t}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="timeframe-buttons">
          {timeframes.map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => onTimeframeChange?.(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <label className="volume-toggle">
        <input
          type="checkbox"
          checked={!!showVolume}
          onChange={(e) => onVolumeToggle?.(e.target.checked)}
        />
        <span>Vol</span>
      </label>
    </div>
  );
};

export default StockSelector;


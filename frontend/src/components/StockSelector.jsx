import React, { useEffect, useMemo, useRef, useState } from 'react';
import './StockSelector.css';

const StockSelector = ({
  ticker,
  validTickers,
  onTickerChange,
  timeframe,
  onTimeframeChange,
  showVolume,
  onVolumeToggle
}) => {
  const timeframes = ['1D', '1W', '1M', '3M', '6M', '1Y'];

  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const [query, setQuery] = useState(ticker);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  /** Keep input synced with selected ticker */
  useEffect(() => {
    setQuery(ticker);
  }, [ticker]);

  /** Filter dropdown options */
  const filteredTickers = useMemo(() => {
    if (!query) return validTickers;
    return validTickers.filter(t =>
      t.toLowerCase().includes(query.toLowerCase())
    );
  }, [query, validTickers]);

  /** Close on outside click */
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
        setQuery(ticker); // revert invalid typing
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [ticker]);

  const commitSelection = (t) => {
    setQuery(t);
    setOpen(false);
    setActiveIndex(0);
    onTickerChange(t);
  };

  const handleKeyDown = (e) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) {
      setOpen(true);
      return;
    }

    if (e.key === 'Escape') {
      setOpen(false);
      setQuery(ticker);
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
      if (filteredTickers[activeIndex]) {
        commitSelection(filteredTickers[activeIndex]);
      }
    }
  };

  return (
    <div className="stock-selector" ref={containerRef}>
      <div className="selector-left">
        {/* TICKER DROPDOWN */}
        <div className="ticker-combobox">
          <input
            ref={inputRef}
            className="ticker-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value.toUpperCase());
              setOpen(true);
              setActiveIndex(0);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder="Select ticker"
            spellCheck={false}
          />

          {open && (
            <div className="ticker-dropdown">
              {filteredTickers.length === 0 ? (
                <div className="ticker-empty">No matches</div>
              ) : (
                filteredTickers.map((t, idx) => (
                  <div
                    key={t}
                    className={`ticker-option ${
                      idx === activeIndex ? 'active' : ''
                    } ${t === ticker ? 'selected' : ''}`}
                    onMouseEnter={() => setActiveIndex(idx)}
                    onMouseDown={(e) => {
                      e.preventDefault(); // prevent blur
                      commitSelection(t);
                    }}
                  >
                    {t}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* TIMEFRAME BUTTONS */}
        <div className="timeframe-buttons">
          {timeframes.map(tf => (
            <button
              key={tf}
              className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => onTimeframeChange(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* VOLUME TOGGLE */}
      <label className="volume-toggle">
        <input
          type="checkbox"
          checked={showVolume}
          onChange={(e) => onVolumeToggle(e.target.checked)}
        />
        <span>Vol</span>
      </label>
    </div>
  );
};

export default StockSelector;

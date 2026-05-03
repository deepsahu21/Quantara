import React from 'react';
import './Header.css';

const Header = ({ onRefresh, demoCaption }) => {
  return (
    <header className="dashboard-header">
      <div className="header-left">
        <div className="logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <path
              d="M16 4L28 16L16 28L4 16L16 4Z"
              stroke="var(--accent-teal)"
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M16 8L24 16L16 24L8 16L16 8Z"
              stroke="var(--accent-blue)"
              strokeWidth="1.5"
              fill="none"
            />
          </svg>
          <span className="logo-text">Quantara</span>
        </div>
        <span className="header-subtitle">AI-Driven Trading Analytics</span>
        {demoCaption ? (
          <span className="header-demo-caption" title={demoCaption}>
            {demoCaption}
          </span>
        ) : null}
      </div>
      <button className="refresh-button" onClick={onRefresh} title="Refresh data">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M10 3V1M10 1L13 4M10 1L7 4M17 10C17 13.866 13.866 17 10 17M17 10C17 6.13401 13.866 3 10 3M10 3C6.13401 3 3 6.13401 3 10M10 17C6.13401 17 3 13.866 3 10M10 17V19M10 19L7 16M10 19L13 16"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        Refresh
      </button>
    </header>
  );
};

export default Header;



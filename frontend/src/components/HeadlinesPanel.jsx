import React from 'react';
import './HeadlinesPanel.css';

const HeadlinesPanel = ({ headlines }) => {
  if (!headlines || !Array.isArray(headlines) || headlines.length === 0) {
    return (
      <div className="headlines-panel">
        <div className="panel-header">
          <span className="panel-title">Recent headlines</span>
        </div>
        <div className="headlines-placeholder">No headlines available</div>
      </div>
    );
  }

  const getSentimentColor = (score) => {
    if (score > 0.5) return 'var(--accent-green)';
    if (score > 0.2) return 'var(--accent-yellow)';
    if (score > -0.2) return 'var(--text-secondary)';
    return 'var(--accent-red)';
  };

  const getSentimentArrow = (score) => {
    if (score > 0) {
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 12L8 4M8 4L4 8M8 4L12 8"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    } else {
      return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 4L8 12M8 12L4 8M8 12L12 8"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    }
  };

  return (
    <div className="headlines-panel">
      <div className="panel-header">
        <span className="panel-title">Recent headlines</span>
      </div>
      <div className="headlines-list">
        {headlines.map((headline, index) => (
          <div key={index} className="headline-item">
            <div className="headline-sentiment">
              <span
                className="sentiment-score"
                style={{ color: getSentimentColor(headline.sentiment_score) }}
              >
                {headline.sentiment_score > 0 ? '+' : ''}{headline.sentiment_score.toFixed(2)}
              </span>
              <span
                className="sentiment-icon"
                style={{ color: getSentimentColor(headline.sentiment_score) }}
              >
                {getSentimentArrow(headline.sentiment_score)}
              </span>
            </div>
            <div className="headline-text">
              {headline.text}
              <span className="headline-arrow"> &gt;&gt;</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HeadlinesPanel;



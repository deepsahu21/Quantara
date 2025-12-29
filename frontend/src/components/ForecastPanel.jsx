import React from 'react';
import './ForecastPanel.css';

const ForecastPanel = ({ directionScore, direction, confidenceBand, confidenceClass }) => {
  const isBullish = direction === 'bullish';
  const arrowRotation = isBullish ? 0 : 180;
  
  // Map confidence class to visual indicator
  const confidenceColor = {
    'Strong': 'var(--accent-green)',
    'Moderate': 'var(--accent-teal)',
    'Low': 'var(--accent-yellow)',
    'Do Not Trade': 'var(--text-muted)'
  }[confidenceClass] || 'var(--text-secondary)';

  return (
    <div className="forecast-panel">
      <div className="panel-header">
        <span className="panel-title">Forecast</span>
        <span className="panel-tag">AI Model</span>
      </div>
      
      <div className="forecast-content">
        <div className="forecast-label">Next day direction:</div>
        
        <div className="direction-indicator">
          <div 
            className="direction-arrow"
            style={{ 
              transform: `rotate(${arrowRotation}deg)`,
              color: isBullish ? 'var(--accent-teal)' : 'var(--accent-red)'
            }}
          >
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 4L12 20M12 20L6 14M12 20L18 14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="direction-value">{Math.abs(directionScore).toFixed(2)}</div>
        </div>
        
        <div className="confidence-section">
          <div className="confidence-label">Confidence band</div>
          <div className="confidence-bar-container">
            <div 
              className="confidence-bar-fill"
              style={{ 
                width: `${confidenceBand * 100}%`,
                backgroundColor: confidenceColor
              }}
            />
          </div>
          <div className="confidence-class">{confidenceClass}</div>
        </div>
        
        <div className="forecast-note">
          Historical simulation performance. Not financial advice.
        </div>
      </div>
    </div>
  );
};

export default ForecastPanel;


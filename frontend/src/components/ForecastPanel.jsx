import React from 'react';
import './ForecastPanel.css';

const ForecastPanel = ({
  direction,
  expectedMovePct,
  confidenceClass,
  confidenceBand
}) => {
  // Guard: no data yet
  if (
    !direction ||
    typeof expectedMovePct !== 'number' ||
    typeof confidenceBand !== 'number'
  ) {
    return (
      <div className="forecast-panel">
        <div className="panel-header">
          <span className="panel-title">Forecast</span>
          <span className="panel-tag">AI Model</span>
        </div>
        <div className="forecast-content muted">—</div>
      </div>
    );
  }

  const isBullish = direction === 'bullish';

  const arrowRotation = isBullish ? 0 : 180;
  const arrowColor = isBullish
    ? 'var(--accent-green)'
    : 'var(--accent-red)';

  const confidenceColorMap = {
    Strong: 'var(--accent-green)',
    Moderate: 'var(--accent-teal)',
    Low: 'var(--accent-yellow)',
    'Very Low': 'var(--text-muted)'
  };

  const confidenceColor =
    confidenceColorMap[confidenceClass] || 'var(--text-muted)';

  const confidenceWidth = Math.round(confidenceBand * 100);

  return (
    <div className="forecast-panel">
      <div className="panel-header">
        <span className="panel-title">Forecast</span>
        <span className="panel-tag">AI Model</span>
      </div>

      <div className="forecast-content">
        <div className="forecast-label">Next day expected move</div>

        <div className="direction-indicator">
          <div
            className="direction-arrow"
            style={{
              transform: `rotate(${arrowRotation}deg)`,
              color: arrowColor
            }}
          >
            ↑
          </div>

          <div className="direction-value">
            {Math.abs(expectedMovePct).toFixed(2)}%
          </div>
        </div>

        <div className="confidence-section">
          <div className="confidence-label">Confidence band</div>

          <div className="confidence-bar-container">
            <div
              className="confidence-bar-fill"
              style={{
                width: `${confidenceWidth}%`,
                backgroundColor: confidenceColor
              }}
            />
          </div>

          <div className="confidence-class">
            {confidenceClass}
          </div>
        </div>

        <div className="forecast-note">
          Historical simulation performance. Not financial advice.
        </div>
      </div>
    </div>
  );
};

export default ForecastPanel;


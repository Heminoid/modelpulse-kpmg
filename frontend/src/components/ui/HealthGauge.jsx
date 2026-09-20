import React, { useEffect, useState } from 'react';
import './HealthGauge.css';

const getStatusColor = (score) => {
  if (score >= 75) return 'var(--status-healthy)';
  if (score >= 55) return 'var(--status-watch)';
  if (score >= 35) return 'var(--status-deteriorating)';
  return 'var(--status-critical)';
};

export const HealthGauge = ({ score = 0, status, size = 'md' }) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(score);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  const sizeMap = {
    sm: 80,
    md: 160,
    lg: 240
  };

  const currentSize = sizeMap[size] || sizeMap.md;
  const strokeWidth = currentSize * 0.1;
  const radius = (currentSize - strokeWidth) / 2;
  const circumference = radius * Math.PI; // Semi-circle
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  const color = getStatusColor(score);

  return (
    <div className={`health-gauge gauge-${size}`} style={{ width: currentSize, height: currentSize / 2 }}>
      <svg
        width={currentSize}
        height={currentSize / 2}
        className="gauge-svg"
        viewBox={`0 0 ${currentSize} ${currentSize / 2}`}
      >
        <path
          className="gauge-bg"
          d={`M ${strokeWidth / 2} ${currentSize / 2} A ${radius} ${radius} 0 0 1 ${currentSize - strokeWidth / 2} ${currentSize / 2}`}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <path
          className="gauge-progress"
          d={`M ${strokeWidth / 2} ${currentSize / 2} A ${radius} ${radius} 0 0 1 ${currentSize - strokeWidth / 2} ${currentSize / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: strokeDashoffset,
          }}
        />
      </svg>
      <div className="gauge-content">
        <span className="gauge-score">{Math.round(score)}</span>
        {status && <span className="gauge-status" style={{ color }}>{status}</span>}
      </div>
    </div>
  );
};

export default HealthGauge;

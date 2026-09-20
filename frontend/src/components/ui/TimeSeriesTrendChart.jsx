import React, { useState } from 'react';
import './TimeSeriesTrendChart.css';

export const TimeSeriesTrendChart = ({ periods = [] }) => {
  const [selectedMetric, setSelectedMetric] = useState('default_rate');
  const [hoveredPoint, setHoveredPoint] = useState(null);

  if (!periods || periods.length === 0) {
    return null;
  }

  const metricConfigs = {
    default_rate: {
      label: 'Default Rate',
      color: '#dc2626',
      fillColor: 'rgba(220, 38, 38, 0.12)',
      format: (v) => `${(v * 100).toFixed(2)}%`,
      getValue: (p) => p.default_rate ?? 0
    },
    mean_score: {
      label: 'Mean Score',
      color: '#00338D',
      fillColor: 'rgba(0, 51, 141, 0.10)',
      format: (v) => Math.round(v).toString(),
      getValue: (p) => p.mean_score ?? 0
    },
    approval_rate: {
      label: 'Approval Rate',
      color: '#00A3A1',
      fillColor: 'rgba(0, 163, 161, 0.12)',
      format: (v) => `${(v * 100).toFixed(1)}%`,
      getValue: (p) => p.approval_rate ?? 0
    }
  };

  // Only offer metrics the backend actually computed for this run's mapped
  // columns — otherwise a missing field (e.g. no `decision` column mapped)
  // would silently draw a confident-looking flat 0% line.
  const availableKeys = Object.keys(metricConfigs).filter((k) =>
    periods.some((p) => p[k] !== undefined && p[k] !== null)
  );

  if (availableKeys.length === 0) {
    return (
      <div className="time-series-trend-chart">
        <div className="empty-state">No trend metrics available for this run's mapped columns.</div>
      </div>
    );
  }

  const activeMetric = availableKeys.includes(selectedMetric) ? selectedMetric : availableKeys[0];
  const config = metricConfigs[activeMetric];
  const values = periods.map(config.getValue);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const valRange = maxVal - minVal || (maxVal > 0 ? maxVal * 0.2 : 1);
  const yMin = Math.max(0, minVal - valRange * 0.15);
  const yMax = maxVal + valRange * 0.15;

  const width = 640;
  const height = 240;
  const padLeft = 60;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 35;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const points = periods.map((p, idx) => {
    const x = padLeft + (periods.length > 1 ? (idx / (periods.length - 1)) * plotWidth : plotWidth / 2);
    const val = config.getValue(p);
    const yRatio = (val - yMin) / (yMax - yMin || 1);
    const y = padTop + plotHeight - yRatio * plotHeight;
    return { x, y, period: p.period, value: val, volume: p.volume };
  });

  const pathData = points.reduce((acc, pt, idx) => {
    return `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
  }, '');

  const areaData = points.length > 0 
    ? `${pathData} L ${points[points.length - 1].x.toFixed(1)} ${(padTop + plotHeight).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padTop + plotHeight).toFixed(1)} Z`
    : '';

  // Y-axis grid ticks (4 ticks)
  const yTicks = [0, 0.33, 0.66, 1].map(r => ({
    y: padTop + plotHeight - r * plotHeight,
    val: yMin + r * (yMax - yMin)
  }));

  // Trend summary
  const firstVal = values[0];
  const lastVal = values[values.length - 1];
  const delta = lastVal - firstVal;
  const deltaPct = firstVal !== 0 ? (delta / firstVal) * 100 : 0;
  const isUp = delta > 0.0001;
  const isDown = delta < -0.0001;

  return (
    <div className="time-series-trend-chart">
      <div className="trend-chart-header">
        <div className="trend-metric-selector">
          {availableKeys.map((k) => (
            <button
              key={k}
              type="button"
              className={`metric-toggle-btn ${activeMetric === k ? 'active' : ''}`}
              onClick={() => setSelectedMetric(k)}
            >
              {metricConfigs[k].label}
            </button>
          ))}
        </div>
        <div className="trend-stats-pill">
          <span className="stat-label">Latest:</span>
          <strong>{config.format(lastVal)}</strong>
          <span className={`trend-delta ${isUp ? (activeMetric === 'default_rate' ? 'trend-worse' : 'trend-better') : (isDown ? (activeMetric === 'default_rate' ? 'trend-better' : 'trend-worse') : 'trend-flat')}`}>
            {isUp ? '↑' : (isDown ? '↓' : '→')} {Math.abs(deltaPct).toFixed(1)}% vs start
          </span>
        </div>
      </div>

      <div className="svg-chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="trend-svg" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id={`grad-${activeMetric}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={config.color} stopOpacity="0.25" />
              <stop offset="100%" stopColor={config.color} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines & Y labels */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line 
                x1={padLeft} 
                y1={t.y} 
                x2={width - padRight} 
                y2={t.y} 
                stroke="var(--border-primary, #e2e8f0)" 
                strokeDasharray="3 3" 
                strokeWidth="1" 
              />
              <text 
                x={padLeft - 8} 
                y={t.y + 4} 
                textAnchor="end" 
                fontSize="11" 
                fill="var(--text-tertiary, #8492a6)"
              >
                {config.format(t.val)}
              </text>
            </g>
          ))}

          {/* Area under curve */}
          {areaData && (
            <path d={areaData} fill={`url(#grad-${activeMetric})`} />
          )}

          {/* Main trend line */}
          {pathData && (
            <path 
              d={pathData} 
              fill="none" 
              stroke={config.color} 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />
          )}

          {/* Data points */}
          {points.map((pt, idx) => (
            <g key={idx}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r={hoveredPoint?.period === pt.period ? 6 : 4}
                fill="var(--bg-card, #ffffff)"
                stroke={config.color}
                strokeWidth="2.5"
                className="chart-dot"
                onMouseEnter={() => setHoveredPoint(pt)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
              {/* X-axis period labels */}
              <text
                x={pt.x}
                y={padTop + plotHeight + 18}
                textAnchor="middle"
                fontSize="11"
                fill="var(--text-secondary, #4a5568)"
                fontWeight="500"
              >
                {pt.period}
              </text>
            </g>
          ))}
        </svg>

        {hoveredPoint && (
          <div 
            className="chart-tooltip"
            style={{
              left: `${(hoveredPoint.x / width) * 100}%`,
              top: `${(hoveredPoint.y / height) * 100}%`
            }}
          >
            <div className="tooltip-period">{hoveredPoint.period}</div>
            <div className="tooltip-metric">
              {config.label}: <strong>{config.format(hoveredPoint.value)}</strong>
            </div>
            {hoveredPoint.volume !== undefined && (
              <div className="tooltip-volume">Volume: {hoveredPoint.volume.toLocaleString()}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TimeSeriesTrendChart;

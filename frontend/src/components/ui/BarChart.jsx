import React, { useState } from 'react';
import './BarChart.css';

// Renders a ChartPayload (chart_type: "bar" or "histogram") as an interactive
// SVG bar chart, consuming the same JSON the backend uses to render report
// images — no image fetch, no matplotlib round-trip.
export const BarChart = ({ series = [], xLabel, yLabel, annotations = [] }) => {
  const [hovered, setHovered] = useState(null);

  const primary = series[0];
  if (!primary || !primary.data || primary.data.length === 0) return null;

  const categories = primary.data.map((d) => String(d.x));
  const allValues = series.flatMap((s) => s.data.map((d) => Number(d.y)));
  const annotationYs = annotations.filter((a) => a.y !== undefined && a.x === undefined).map((a) => Number(a.y));
  const allY = [...allValues, ...annotationYs, 0];
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const range = yMax - yMin || (yMax !== 0 ? Math.abs(yMax) * 0.2 : 1);
  const paddedMax = yMax + range * 0.15;
  const paddedMin = yMin < 0 ? yMin - range * 0.1 : 0;

  const width = 640;
  const height = 280;
  const padLeft = 56;
  const padRight = 24;
  const padTop = 20;
  const padBottom = categories.some((c) => c.length > 6) ? 56 : 34;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const yToPx = (v) => padTop + plotHeight - ((v - paddedMin) / (paddedMax - paddedMin || 1)) * plotHeight;
  const zeroY = yToPx(0);

  const seriesCount = series.length;
  const groupWidth = plotWidth / (categories.length || 1);
  const barWidth = Math.min((groupWidth * 0.7) / seriesCount, 42);

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => paddedMin + r * (paddedMax - paddedMin));

  return (
    <div className="mini-bar-chart">
      {series.length > 1 && (
        <div className="chart-legend">
          {series.map((s) => (
            <span key={s.name} className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: s.color || '#0091DA' }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
      <div className="svg-chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="mini-chart-svg" preserveAspectRatio="xMidYMid meet">
          {yTicks.map((t, i) => (
            <g key={i}>
              <line x1={padLeft} y1={yToPx(t)} x2={width - padRight} y2={yToPx(t)} stroke="var(--border-primary, #e2e8f0)" strokeDasharray="3 3" strokeWidth="1" />
              <text x={padLeft - 8} y={yToPx(t) + 4} textAnchor="end" fontSize="10" fill="var(--text-tertiary, #8492a6)">
                {Math.abs(t) >= 1000 ? t.toFixed(0) : t.toFixed(2)}
              </text>
            </g>
          ))}

          {categories.map((cat, i) => {
            const groupX = padLeft + i * groupWidth + (groupWidth - barWidth * seriesCount) / 2;
            return (
              <g key={i}>
                {series.map((s, si) => {
                  const point = s.data[i];
                  if (!point) return null;
                  const val = Number(point.y);
                  const barY = Math.min(yToPx(val), zeroY);
                  const barH = Math.max(1, Math.abs(yToPx(val) - zeroY));
                  const x = groupX + si * barWidth;
                  const isHovered = hovered?.catIndex === i && hovered?.seriesIndex === si;
                  return (
                    <rect
                      key={si}
                      x={x}
                      y={barY}
                      width={barWidth - 2}
                      height={barH}
                      fill={s.color || '#0091DA'}
                      opacity={isHovered ? 1 : 0.85}
                      rx="2"
                      className="mini-bar"
                      onMouseEnter={() => setHovered({ catIndex: i, seriesIndex: si, cat, val, name: s.name, x: x + barWidth / 2, y: barY })}
                      onMouseLeave={() => setHovered(null)}
                    />
                  );
                })}
              </g>
            );
          })}

          {categories.map((cat, i) => {
            const x = padLeft + i * groupWidth + groupWidth / 2;
            const long = categories.some((c) => c.length > 6);
            return (
              <text
                key={`lbl-${i}`}
                x={x}
                y={padTop + plotHeight + (long ? 14 : 18)}
                textAnchor={long ? 'end' : 'middle'}
                fontSize="10"
                fill="var(--text-secondary, #4a5568)"
                transform={long ? `rotate(-40 ${x} ${padTop + plotHeight + 14})` : undefined}
              >
                {cat.length > 14 ? cat.slice(0, 12) + '…' : cat}
              </text>
            );
          })}

          {annotations.filter((a) => a.y !== undefined && a.x === undefined).map((a, i) => (
            <g key={`ann-${i}`}>
              <line x1={padLeft} y1={yToPx(a.y)} x2={width - padRight} y2={yToPx(a.y)} stroke={a.color || '#94a3b8'} strokeDasharray="5 3" strokeWidth="1.5" />
              {a.label && (
                <text x={width - padRight} y={yToPx(a.y) - 4} textAnchor="end" fontSize="10" fontWeight="600" fill={a.color || '#94a3b8'}>
                  {a.label}
                </text>
              )}
            </g>
          ))}

          {xLabel && (
            <text x={padLeft + plotWidth / 2} y={height - 4} textAnchor="middle" fontSize="10" fill="var(--text-tertiary, #8492a6)">
              {xLabel}
            </text>
          )}
        </svg>

        {hovered && (
          <div className="mini-chart-tooltip" style={{ left: `${(hovered.x / width) * 100}%`, top: `${(hovered.y / height) * 100}%` }}>
            {series.length > 1 && <div className="tooltip-series-name">{hovered.name}</div>}
            <div className="tooltip-cat">{hovered.cat}</div>
            <div className="tooltip-val">
              {yLabel ? `${yLabel}: ` : ''}<strong>{Math.abs(hovered.val) < 10 ? hovered.val.toFixed(4) : hovered.val.toFixed(1)}</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BarChart;

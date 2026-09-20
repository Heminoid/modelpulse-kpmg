import React, { useState } from 'react';
import './LineChart.css';

// Renders a ChartPayload (chart_type: "line" or "scatter") as an interactive
// SVG line chart — supports multiple named series and reference-line
// annotations (horizontal, vertical, or diagonal), read straight from the
// same JSON the backend uses to render report images.
export const LineChart = ({ series = [], xLabel, yLabel, annotations = [] }) => {
  const [hovered, setHovered] = useState(null);

  if (!series.length || !series[0].data?.length) return null;

  // x is numeric if every point's x parses cleanly to a finite number
  // (e.g. ROC curve FPR values); otherwise treat x as ordered categories
  // (e.g. "Bin 1".."Bin 10").
  const allXRaw = series.flatMap((s) => s.data.map((d) => d.x));
  const isNumericX = allXRaw.every((x) => x !== '' && x !== null && Number.isFinite(Number(x)));
  const categories = isNumericX ? null : [...new Set(allXRaw.map(String))];

  const xOf = (x, idx) => (isNumericX ? Number(x) : idx);

  const allX = isNumericX ? allXRaw.map(Number) : series[0].data.map((_, i) => i);
  const allY = series.flatMap((s) => s.data.map((d) => Number(d.y)));
  const annotationVals = annotations.flatMap((a) => [a.x, a.y]).filter((v) => v !== undefined).map(Number);

  const xMin = Math.min(...allX, ...(isNumericX ? annotationVals : []));
  const xMax = Math.max(...allX, ...(isNumericX ? annotationVals : []));
  const yMin = Math.min(0, ...allY, ...annotationVals);
  const yMax = Math.max(...allY, ...annotationVals, 0);
  const yRange = yMax - yMin || 1;
  const paddedYMax = yMax + yRange * 0.12;
  const paddedYMin = yMin - yRange * 0.05;

  const width = 640;
  const height = 280;
  const padLeft = 56;
  const padRight = 24;
  const padTop = 20;
  const padBottom = 34;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const xScale = (x) => {
    if (isNumericX) {
      return padLeft + ((x - xMin) / (xMax - xMin || 1)) * plotWidth;
    }
    return padLeft + (categories.length > 1 ? (x / (categories.length - 1)) * plotWidth : plotWidth / 2);
  };
  const yScale = (y) => padTop + plotHeight - ((y - paddedYMin) / (paddedYMax - paddedYMin || 1)) * plotHeight;

  const seriesPoints = series.map((s) => ({
    ...s,
    points: s.data.map((d, i) => ({
      x: xScale(xOf(d.x, categories ? categories.indexOf(String(d.x)) : i)),
      y: yScale(Number(d.y)),
      rawX: d.x,
      rawY: Number(d.y),
    })),
  }));

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => paddedYMin + r * (paddedYMax - paddedYMin));
  const xTickLabels = isNumericX
    ? [xMin, xMin + (xMax - xMin) / 2, xMax]
    : categories;

  return (
    <div className="mini-line-chart">
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
              <line x1={padLeft} y1={yScale(t)} x2={width - padRight} y2={yScale(t)} stroke="var(--border-primary, #e2e8f0)" strokeDasharray="3 3" strokeWidth="1" />
              <text x={padLeft - 8} y={yScale(t) + 4} textAnchor="end" fontSize="10" fill="var(--text-tertiary, #8492a6)">
                {Math.abs(t) >= 100 ? t.toFixed(0) : t.toFixed(2)}
              </text>
            </g>
          ))}

          {/* Reference-line annotations: y-only -> horizontal, x-only -> vertical, both -> diagonal to top-right */}
          {annotations.map((a, i) => {
            if (a.y !== undefined && a.x === undefined) {
              return (
                <g key={`ann-${i}`}>
                  <line x1={padLeft} y1={yScale(a.y)} x2={width - padRight} y2={yScale(a.y)} stroke={a.color || '#94a3b8'} strokeDasharray="5 3" strokeWidth="1.5" />
                  {a.label && <text x={width - padRight} y={yScale(a.y) - 4} textAnchor="end" fontSize="10" fontWeight="600" fill={a.color || '#94a3b8'}>{a.label}</text>}
                </g>
              );
            }
            if (a.x !== undefined && a.y === undefined) {
              const xPos = xScale(a.x);
              return (
                <line key={`ann-${i}`} x1={xPos} y1={padTop} x2={xPos} y2={padTop + plotHeight} stroke={a.color || '#94a3b8'} strokeDasharray="5 3" strokeWidth="1.5" />
              );
            }
            if (a.x !== undefined && a.y !== undefined) {
              return (
                <line
                  key={`ann-${i}`}
                  x1={xScale(a.x)} y1={yScale(a.y)}
                  x2={xScale(xMax)} y2={yScale(yMax)}
                  stroke={a.color || '#94a3b8'}
                  strokeDasharray="4 4"
                  strokeWidth="1.5"
                />
              );
            }
            return null;
          })}

          {seriesPoints.map((s, si) => {
            const path = s.points.reduce((acc, pt, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`, '');
            return (
              <g key={si}>
                <path d={path} fill="none" stroke={s.color || '#0091DA'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                {s.points.map((pt, pi) => (
                  <circle
                    key={pi}
                    cx={pt.x}
                    cy={pt.y}
                    r={hovered?.si === si && hovered?.pi === pi ? 5.5 : 3}
                    fill="var(--bg-card, #ffffff)"
                    stroke={s.color || '#0091DA'}
                    strokeWidth="2"
                    className="mini-line-dot"
                    onMouseEnter={() => setHovered({ si, pi, x: pt.x, y: pt.y, rawX: pt.rawX, rawY: pt.rawY, name: s.name })}
                    onMouseLeave={() => setHovered(null)}
                  />
                ))}
              </g>
            );
          })}

          {xTickLabels.map((label, i) => {
            const x = isNumericX ? xScale(label) : xScale(i);
            const text = isNumericX ? Number(label).toFixed(2) : (String(label).length > 10 ? String(label).slice(0, 8) + '…' : label);
            return (
              <text key={i} x={x} y={padTop + plotHeight + 18} textAnchor="middle" fontSize="10" fill="var(--text-secondary, #4a5568)">
                {text}
              </text>
            );
          })}

          {xLabel && (
            <text x={padLeft + plotWidth / 2} y={height - 4} textAnchor="middle" fontSize="10" fill="var(--text-tertiary, #8492a6)">
              {xLabel}
            </text>
          )}
        </svg>

        {hovered && (
          <div className="mini-chart-tooltip" style={{ left: `${(hovered.x / width) * 100}%`, top: `${(hovered.y / height) * 100}%` }}>
            {series.length > 1 && <div className="tooltip-series-name">{hovered.name}</div>}
            <div className="tooltip-val">
              {xLabel || 'x'}: <strong>{typeof hovered.rawX === 'number' ? hovered.rawX.toFixed(3) : hovered.rawX}</strong>
            </div>
            <div className="tooltip-val">
              {yLabel || 'y'}: <strong>{hovered.rawY.toFixed(4)}</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LineChart;

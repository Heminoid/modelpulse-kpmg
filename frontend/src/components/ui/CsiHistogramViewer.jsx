import React, { useState } from 'react';
import Badge from './Badge';
import './CsiHistogramViewer.css';

export const CsiHistogramViewer = ({ featureData = [] }) => {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [hoveredBin, setHoveredBin] = useState(null);

  if (!featureData || featureData.length === 0) {
    return null;
  }

  const selected = featureData[selectedIdx] || featureData[0];
  const bHist = selected.baseline_histogram || {};
  const cHist = selected.current_histogram || {};

  const bCounts = bHist.counts || [];
  const cCounts = cHist.counts || [];
  const binEdges = bHist.bin_edges || [];

  const bTotal = bCounts.reduce((a, b) => a + b, 0) || 1;
  const cTotal = cCounts.reduce((a, b) => a + b, 0) || 1;

  const nBins = Math.min(bCounts.length, cCounts.length);
  const bins = [];
  for (let i = 0; i < nBins; i++) {
    const bCount = bCounts[i];
    const cCount = cCounts[i];
    const bPct = (bCount / bTotal) * 100;
    const cPct = (cCount / cTotal) * 100;
    const rangeLabel = binEdges.length > i + 1 
      ? `${binEdges[i]}–${binEdges[i + 1]}`
      : `Bin ${i + 1}`;
    
    // Bin contribution
    const bFrac = bCount / bTotal + 1e-4;
    const cFrac = cCount / cTotal + 1e-4;
    const contribution = (cFrac - bFrac) * Math.log(cFrac / bFrac);

    bins.push({
      bin: i + 1,
      range: rangeLabel,
      bCount,
      cCount,
      bPct,
      cPct,
      delta: cPct - bPct,
      contribution
    });
  }

  const maxPct = Math.max(
    ...bins.map(b => Math.max(b.bPct, b.cPct)),
    10
  );

  const width = 640;
  const height = 240;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 25;
  const padBottom = 40;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const groupWidth = plotWidth / (bins.length || 1);
  const barWidth = Math.min(groupWidth * 0.38, 28);
  const barGap = 4;

  const getStatusBadge = (status) => {
    if (status === 'critical') return <Badge status="critical" size="sm">CRITICAL</Badge>;
    if (status === 'warning') return <Badge status="watch" size="sm">WARNING</Badge>;
    return <Badge status="healthy" size="sm">STABLE</Badge>;
  };

  const currentColor = selected.status === 'critical' ? '#dc2626' : (selected.status === 'warning' ? '#d97706' : '#0091DA');

  return (
    <div className="csi-histogram-viewer panel">
      <div className="csi-viewer-header">
        <div className="csi-viewer-title-row">
          <h4>Feature Drift Distribution Explorer</h4>
          <span className="csi-viewer-subtitle">Distribution Shift vs Baseline Histogram</span>
        </div>
        <div className="csi-feature-selector">
          <label htmlFor="csi-feature-select">Feature:</label>
          <select 
            id="csi-feature-select"
            value={selectedIdx} 
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            className="csi-select"
          >
            {featureData.map((f, i) => (
              <option key={f.feature} value={i}>
                {f.feature.replace(/_/g, ' ')} (CSI: {f.csi_value?.toFixed(4) || '0.0000'})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="csi-feature-kpis">
        <div className="csi-kpi-item">
          <span className="kpi-label">Selected Feature</span>
          <span className="kpi-value feature-name">{selected.feature}</span>
        </div>
        <div className="csi-kpi-item">
          <span className="kpi-label">CSI Value</span>
          <span className="kpi-value font-mono">{selected.csi_value?.toFixed(4) ?? 'N/A'}</span>
        </div>
        <div className="csi-kpi-item">
          <span className="kpi-label">Status</span>
          <span className="kpi-badge">{getStatusBadge(selected.status)}</span>
        </div>
        <div className="csi-kpi-item legend-item">
          <span className="legend-chip baseline-chip"></span> Baseline
          <span className="legend-chip current-chip" style={{ backgroundColor: currentColor }}></span> Current
        </div>
      </div>

      <div className="csi-chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="csi-svg" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
            const y = padTop + plotHeight - r * plotHeight;
            const pct = (r * maxPct).toFixed(0);
            return (
              <g key={i}>
                <line 
                  x1={padLeft} 
                  y1={y} 
                  x2={width - padRight} 
                  y2={y} 
                  stroke="var(--border-primary, #e2e8f0)" 
                  strokeDasharray="2 2" 
                  strokeWidth="1" 
                />
                <text 
                  x={padLeft - 6} 
                  y={y + 4} 
                  textAnchor="end" 
                  fontSize="10" 
                  fill="var(--text-tertiary, #8492a6)"
                >
                  {pct}%
                </text>
              </g>
            );
          })}

          {/* Bars */}
          {bins.map((bin, i) => {
            const groupX = padLeft + i * groupWidth + (groupWidth - (barWidth * 2 + barGap)) / 2;
            const bBarH = (bin.bPct / maxPct) * plotHeight;
            const cBarH = (bin.cPct / maxPct) * plotHeight;
            const bY = padTop + plotHeight - bBarH;
            const cY = padTop + plotHeight - cBarH;

            return (
              <g 
                key={i} 
                className="bin-group"
                onMouseEnter={() => setHoveredBin(bin)}
                onMouseLeave={() => setHoveredBin(null)}
              >
                {/* Baseline bar */}
                <rect
                  x={groupX}
                  y={bY}
                  width={barWidth}
                  height={Math.max(0, bBarH)}
                  fill="#00338D"
                  rx="3"
                  className="hist-bar baseline-bar"
                />
                {/* Current bar */}
                <rect
                  x={groupX + barWidth + barGap}
                  y={cY}
                  width={barWidth}
                  height={Math.max(0, cBarH)}
                  fill={currentColor}
                  rx="3"
                  className="hist-bar current-bar"
                />
                {/* X label */}
                <text
                  x={groupX + barWidth + barGap / 2}
                  y={padTop + plotHeight + 16}
                  textAnchor="middle"
                  fontSize="9.5"
                  fill="var(--text-secondary, #4a5568)"
                >
                  {bin.range.length > 12 ? bin.range.slice(0, 10) + '..' : bin.range}
                </text>
              </g>
            );
          })}
        </svg>

        {hoveredBin && (
          <div className="csi-tooltip">
            <div className="tooltip-bin-range">Bin: {hoveredBin.range}</div>
            <div className="tooltip-row">
              <span className="tooltip-dot baseline"></span> Baseline: <strong>{hoveredBin.bPct.toFixed(1)}%</strong> ({hoveredBin.bCount.toLocaleString()})
            </div>
            <div className="tooltip-row">
              <span className="tooltip-dot current"></span> Current: <strong>{hoveredBin.cPct.toFixed(1)}%</strong> ({hoveredBin.cCount.toLocaleString()})
            </div>
            <div className="tooltip-row delta">
              Shift: <strong>{hoveredBin.delta > 0 ? '+' : ''}{hoveredBin.delta.toFixed(1)}%</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CsiHistogramViewer;

import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import './KPICard.css';

const statusColors = {
  healthy: 'var(--status-healthy)',
  watch: 'var(--status-watch)',
  deteriorating: 'var(--status-deteriorating)',
  critical: 'var(--status-critical)',
  info: 'var(--status-info)'
};

export const KPICard = ({ title, value, unit, status = 'info', baseline, explanation, icon: Icon }) => {
  const accentColor = statusColors[status] || statusColors.info;
  
  const renderDelta = () => {
    if (!baseline || baseline === 0) return null;
    const delta = ((value - baseline) / baseline) * 100;
    if (delta === 0) return null;
    
    const isPositive = delta > 0;
    return (
      <div className={`kpi-delta ${isPositive ? 'positive' : 'negative'}`}>
        {isPositive ? <ArrowUp className="kpi-delta-icon" /> : <ArrowDown className="kpi-delta-icon" />}
        {Math.abs(delta).toFixed(1)}%
      </div>
    );
  };

  return (
    <div className="kpi-card" style={{ borderLeftColor: accentColor }} title={explanation}>
      <div className="kpi-header">
        <span className="kpi-title">{title}</span>
        {Icon && <Icon className="kpi-icon" />}
      </div>
      <div className="kpi-body">
        <div className="kpi-value-container">
          <span className="kpi-value">{value}</span>
          {unit && <span className="kpi-unit">{unit}</span>}
        </div>
        {renderDelta()}
      </div>
    </div>
  );
};

export default KPICard;

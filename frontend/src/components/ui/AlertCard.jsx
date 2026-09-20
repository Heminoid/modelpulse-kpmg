import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import './AlertCard.css';

export const AlertCard = ({ alert }) => {
  const { severity, metric_key, message } = alert;
  const value = alert.observed_value ?? alert.value;
  const threshold = alert.threshold_value ?? alert.threshold;
  
  const isCritical = severity === 'critical';
  const isWarning = severity === 'warning' || severity === 'watch';
  const Icon = isCritical ? AlertCircle : (isWarning ? AlertTriangle : Info);
  const severityClass = isCritical ? 'alert-critical' : (isWarning ? 'alert-warning' : 'alert-info');
  
  const formatMetricKey = (key) => {
    if (!key) return '';
    return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  return (
    <div className={`alert-card ${severityClass}`}>
      <div className="alert-icon-wrapper">
        <Icon className="alert-icon" />
      </div>
      <div className="alert-content">
        <div className="alert-header">
          <span className="alert-metric">{formatMetricKey(metric_key)}</span>
          <span className="alert-severity-badge">{severity}</span>
        </div>
        <p className="alert-message">{message}</p>
        <div className="alert-details">
          <span className="alert-value">Observed: <strong>{typeof value === 'number' ? value.toFixed(4) : (value ?? 'N/A')}</strong></span>
          <span className="alert-threshold">Threshold: <strong>{threshold ?? 'N/A'}</strong></span>
        </div>
      </div>
    </div>
  );
};

export default AlertCard;

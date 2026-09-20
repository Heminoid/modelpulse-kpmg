import React from 'react';
import { CheckCircle, AlertTriangle, AlertCircle, Info, XCircle } from 'lucide-react';
import './Badge.css';

const statusMap = {
  ok: 'healthy',
  healthy: 'healthy',
  warning: 'watch',
  watch: 'watch',
  deteriorating: 'deteriorating',
  breached: 'critical',
  critical: 'critical',
  error: 'critical',
  info: 'info',
  skipped: 'info'
};

const iconMap = {
  healthy: CheckCircle,
  watch: AlertTriangle,
  deteriorating: AlertCircle,
  critical: XCircle,
  info: Info
};

export const Badge = ({ status = 'info', size = 'md', children, className = '' }) => {
  const normalizedStatus = statusMap[status.toLowerCase()] || 'info';
  const Icon = iconMap[normalizedStatus];

  return (
    <span className={`badge badge-${normalizedStatus} badge-${size}${className ? ' ' + className : ''}`}>
      {Icon && <Icon className="badge-icon" />}
      {children || status}
    </span>
  );
};

export default Badge;

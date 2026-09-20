import React, { useEffect, useState } from 'react';
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import './Toast.css';

const toastIcons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info
};

export const Toast = ({ id, message, type = 'info', duration = 4000, onClose }) => {
  const [isClosing, setIsClosing] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose(id);
    }, 300); // Wait for exit animation
  };

  const Icon = toastIcons[type];

  return (
    <div className={`toast toast-${type} ${isClosing ? 'toast-exit' : 'toast-enter'}`}>
      <div className="toast-content">
        <Icon className="toast-icon" />
        <p className="toast-message">{message}</p>
      </div>
      <button className="toast-close" onClick={handleClose} aria-label="Close toast">
        <X size={16} />
      </button>
      <div className="toast-progress-bar" style={{ animationDuration: `${duration}ms` }} />
    </div>
  );
};

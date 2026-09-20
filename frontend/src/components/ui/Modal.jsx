import React, { useEffect, useRef } from 'react';
import { X, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import './Modal.css';

const variantIcons = {
  info: Info,
  warning: AlertTriangle,
  danger: AlertCircle
};

export const Modal = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  children,
  variant = 'info',
  confirmText = 'Confirm',
  cancelText = 'Cancel'
}) => {
  const modalRef = useRef(null);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const Icon = variantIcons[variant];
  const btnClass = variant === 'danger' ? 'btn-danger' : 'btn-primary';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-content animate-scale-in" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        ref={modalRef}
      >
        <div className="modal-header">
          <div className="modal-title-wrapper">
            {Icon && <Icon className={`modal-icon variant-${variant}`} />}
            <h2 className="modal-title">{title}</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>
        
        <div className="modal-body">
          {children}
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            {cancelText}
          </button>
          <button className={`btn ${btnClass}`} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Modal;

import React from 'react';
import './Card.css';

const Card = ({ title, subtitle, icon: Icon, children, className = '', action, noPadding = false }) => {
  return (
    <div className={`card glass-panel ${className}`}>
      {(title || Icon || action) && (
        <div className="card-header">
          <div className="card-header-left">
            {Icon && (
              <div className="card-icon-wrapper">
                <Icon size={20} className="card-icon" />
              </div>
            )}
            <div>
              {title && <h3 className="card-title">{title}</h3>}
              {subtitle && <p className="card-subtitle">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="card-action">{action}</div>}
        </div>
      )}
      <div className={`card-body ${noPadding ? 'p-0' : ''}`}>
        {children}
      </div>
    </div>
  );
};

export default Card;

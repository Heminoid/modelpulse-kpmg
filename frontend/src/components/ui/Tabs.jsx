import React, { useRef, useEffect } from 'react';
import './Tabs.css';

export const Tabs = ({ tabs = [], activeTab, onChange }) => {
  const tabsRef = useRef([]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      const currentIndex = tabs.findIndex(tab => tab.id === activeTab);
      if (currentIndex === -1) return;

      if (e.key === 'ArrowRight') {
        const nextIndex = (currentIndex + 1) % tabs.length;
        onChange(tabs[nextIndex].id);
        tabsRef.current[nextIndex]?.focus();
      } else if (e.key === 'ArrowLeft') {
        const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
        onChange(tabs[prevIndex].id);
        tabsRef.current[prevIndex]?.focus();
      }
    };

    const tabList = document.querySelector('.tabs-list');
    tabList?.addEventListener('keydown', handleKeyDown);
    return () => tabList?.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, tabs, onChange]);

  return (
    <div className="tabs-container">
      <div className="tabs-list" role="tablist" aria-label="Navigation Tabs">
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              ref={el => tabsRef.current[index] = el}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              className={`tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => onChange(tab.id)}
            >
              <div className="tab-content">
                {tab.icon && <tab.icon className="tab-icon" />}
                <span className="tab-label">{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className="tab-badge">{tab.badge}</span>
                )}
              </div>
              {isActive && <div className="tab-indicator layout-id-indicator" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default Tabs;

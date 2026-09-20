import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Database, Activity, FileText, Settings, PlayCircle, Box, Menu, X, Grid3X3 } from 'lucide-react';
import ThemeToggle from './ui/ThemeToggle';
import './Sidebar.css';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/portfolio', label: 'Portfolio', icon: Grid3X3 },
  { path: '/registry', label: 'Model Registry', icon: Box },
  { path: '/datasets', label: 'Datasets', icon: Database },
  { path: '/monitors', label: 'Monitors', icon: Activity },
  { path: '/runs', label: 'Runs', icon: PlayCircle },
  { path: '/reports', label: 'Reports', icon: FileText },
];

const Sidebar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <>
      <button
        className="mobile-menu-btn"
        onClick={toggleSidebar}
        aria-label={isOpen ? 'Close navigation menu' : 'Open navigation menu'}
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>
      
      <div className={`sidebar glass-panel ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo-container" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <Activity className="logo-icon" size={28} color="var(--brand-teal)" />
            <span className="logo-text">ModelPulse</span>
          </div>
        </div>
        
        <div className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-item ${isActive || location.pathname === item.path ? 'active' : ''}`}
                onClick={() => setIsOpen(false)}
              >
                <Icon size={20} className="nav-icon" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        <div className="sidebar-footer" style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.875rem 1rem' }}>
          <img src="/kpmg-logo.png" alt="KPMG" style={{ height: '35px', filter: 'brightness(0) invert(1)', opacity: 0.9 }} />
          <ThemeToggle />
        </div>
      </div>
      
      {isOpen && <div className="sidebar-overlay" onClick={toggleSidebar}></div>}
    </>
  );
};

export default Sidebar;

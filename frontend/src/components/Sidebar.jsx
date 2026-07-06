import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Database, Activity, FileText, Settings, PlayCircle, Box } from 'lucide-react';
import './Sidebar.css'; // We'll add some specific sidebar styles

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/registry', label: 'Model Registry', icon: Box },
  { path: '/datasets', label: 'Datasets', icon: Database },
  { path: '/monitors', label: 'Monitors', icon: Activity },
  { path: '/runs', label: 'Runs', icon: PlayCircle },
  { path: '/reports', label: 'Reports', icon: FileText },
];

const Sidebar = () => {
  return (
    <div className="sidebar glass-panel">
      <div className="sidebar-header">
        <div className="logo-container">
          <Activity className="logo-icon" size={28} color="var(--accent-secondary)" />
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
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={20} className="nav-icon" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <button className="nav-item settings-btn">
          <Settings size={20} className="nav-icon" />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;

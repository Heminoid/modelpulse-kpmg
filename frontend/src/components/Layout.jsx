import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import WorkflowStepper from './ui/WorkflowStepper';

const Layout = () => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100%' }}>
      <Sidebar />
      <main className="page-container animate-fade-in">
        <WorkflowStepper />
        <Outlet />
      </main>
      <div className="toast-viewport" />
    </div>
  );
};

export default Layout;

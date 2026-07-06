import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const Layout = () => {
  return (
    <>
      <Sidebar />
      <main className="page-container animate-fade-in">
        <Outlet />
      </main>
    </>
  );
};

export default Layout;

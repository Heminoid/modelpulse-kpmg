import React, { useEffect } from 'react';
import './styles/theme.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Datasets from './pages/Datasets';
import DatasetDetail from './pages/DatasetDetail';
import Monitors from './pages/Monitors';
import Registry from './pages/Registry';
import Runs from './pages/Runs';
import Reports from './pages/Reports';
import Portfolio from './pages/Portfolio';
import { ToastProvider } from './components/ui/ToastContext';

function App() {
  useEffect(() => {
    const theme = localStorage.getItem('modelpulse-theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
  }, []);

  return (
    <ToastProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="datasets" element={<Datasets />} />
            <Route path="datasets/:id" element={<DatasetDetail />} />
            <Route path="monitors" element={<Monitors />} />
            <Route path="registry" element={<Registry />} />
            <Route path="runs" element={<Runs />} />
            <Route path="portfolio" element={<Portfolio />} />
            <Route path="reports" element={<Reports />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;

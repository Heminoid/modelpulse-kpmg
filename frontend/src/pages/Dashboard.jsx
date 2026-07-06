import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getHealth, getDatasets, getMonitors, getRuns } from '../services/api';
import { Server, Database, Activity, PlayCircle, AlertTriangle, CheckCircle2 } from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, color, loading }) => (
  <Card className="stat-card" icon={Icon}>
    <div style={{ marginTop: '1rem' }}>
      <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>{title}</h4>
      {loading ? (
        <div className="skeleton-loader" style={{ height: '2rem', width: '60%' }}></div>
      ) : (
        <div style={{ fontSize: '2rem', fontWeight: '700', color: color || 'var(--text-primary)' }}>
          {value}
        </div>
      )}
    </div>
  </Card>
);

const Dashboard = () => {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState({ datasets: 0, monitors: 0, runs: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [healthRes, datasetsRes, monitorsRes, runsRes] = await Promise.all([
          getHealth().catch(() => ({ status: 'error' })),
          getDatasets().catch(() => ({ total: 0 })),
          getMonitors().catch(() => ({ data: [] })),
          getRuns().catch(() => ({ data: [] }))
        ]);

        setHealth(healthRes);
        setStats({
          datasets: datasetsRes.total || (datasetsRes.data ? datasetsRes.data.length : 0),
          monitors: monitorsRes.data ? monitorsRes.data.length : 0,
          runs: runsRes.data ? runsRes.data.length : 0,
        });
      } catch (error) {
        console.error("Failed to load dashboard data", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const isHealthy = health?.data?.status === 'ok';

  return (
    <div className="dashboard-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome to ModelPulse monitoring platform.</p>
        </div>
        <div className="health-badge glass-panel" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: 'var(--radius-xl)' }}>
          {loading ? (
            <span style={{ color: 'var(--text-muted)' }}>Checking system...</span>
          ) : isHealthy ? (
            <><CheckCircle2 color="var(--success)" size={18} /> <span style={{ color: 'var(--success)', fontWeight: '600' }}>System Online</span></>
          ) : (
            <><AlertTriangle color="var(--warning)" size={18} /> <span style={{ color: 'var(--warning)', fontWeight: '600' }}>System Offline</span></>
          )}
        </div>
      </div>

      <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginTop: '1rem' }}>
        <StatCard title="Total Datasets" value={stats.datasets} icon={Database} loading={loading} color="var(--accent-primary)" />
        <StatCard title="Active Monitors" value={stats.monitors} icon={Activity} loading={loading} color="var(--success)" />
        <StatCard title="Total Runs" value={stats.runs} icon={PlayCircle} loading={loading} color="var(--warning)" />
        <StatCard title="API Status" value={isHealthy ? "OK" : "Error"} icon={Server} loading={loading} color={isHealthy ? "var(--success)" : "var(--error)"} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
        <Card title="Recent Activity" icon={Activity}>
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '3rem 0' }}>
            No recent activity found. Configure a monitor to get started.
          </div>
        </Card>
        
        <Card title="Quick Actions">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => window.location.href = '/datasets'}>Upload Dataset</button>
            <button className="btn btn-secondary" style={{ width: '100%' }} onClick={() => window.location.href = '/monitors'}>Create Monitor</button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;

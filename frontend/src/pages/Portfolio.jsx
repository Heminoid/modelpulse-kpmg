import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMonitors, getRuns, getRunHealth, getRunAlerts } from '../services/api';
import HealthGauge from '../components/ui/HealthGauge';
import Badge from '../components/ui/Badge';
import KPICard from '../components/ui/KPICard';
import { useToast } from '../components/ui/ToastContext';
import { Activity, AlertTriangle, TrendingUp, TrendingDown, Grid3X3, ArrowUpRight } from 'lucide-react';
import './Portfolio.css';

const Portfolio = () => {
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortOrder, setSortOrder] = useState('health'); // 'name', 'health', 'alerts'
  const { addToast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPortfolioData = async () => {
      try {
        setLoading(true);
        const [monitorsRes, runsRes] = await Promise.all([
          getMonitors(),
          getRuns()
        ]);
        
        const allMonitors = monitorsRes.data || [];
        const allRuns = runsRes.data || [];

        // For each monitor, find latest run and health + alerts
        const enriched = await Promise.all(allMonitors.map(async (monitor) => {
          const run = allRuns.find(r => r.monitor_id === monitor.monitor_id);
          let healthData = { score: 0, status: 'unknown', alerts: 0 };
          if (run) {
            try {
              const [hRes, aRes] = await Promise.all([
                getRunHealth(run.run_id).catch(() => ({ data: { score: 0, status: 'unknown' } })),
                getRunAlerts(run.run_id).catch(() => ({ data: [] }))
              ]);
              const alertList = Array.isArray(aRes?.data) ? aRes.data : [];
              healthData = { ...hRes.data, alerts: alertList.length };
            } catch (e) {
              console.error(e);
            }
          }
          return {
            ...monitor,
            latestRun: run,
            health: healthData
          };
        }));
        
        setMonitors(enriched);
      } catch (err) {
        addToast({ message: 'Failed to load portfolio data', type: 'error' });
      } finally {
        setLoading(false);
      }
    };
    fetchPortfolioData();
  }, [addToast]);

  const kpis = useMemo(() => {
    if (!monitors.length) return { total: 0, avgHealth: 0, critical: 0, healthy: 0 };
    const withRuns = monitors.filter(m => m.latestRun);
    if (!withRuns.length) return { total: monitors.length, avgHealth: 0, critical: 0, healthy: 0 };
    
    const avgHealth = Math.round(withRuns.reduce((acc, m) => acc + (m.health?.score || 0), 0) / withRuns.length);
    const critical = withRuns.filter(m => (m.health?.score || 0) < 50).length;
    const healthy = withRuns.filter(m => (m.health?.score || 0) >= 90).length;
    return { total: monitors.length, avgHealth, critical, healthy };
  }, [monitors]);

  const sortedMonitors = useMemo(() => {
    const sorted = [...monitors];
    if (sortOrder === 'name') {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortOrder === 'health') {
      sorted.sort((a, b) => (a.health?.score || 0) - (b.health?.score || 0));
    } else if (sortOrder === 'alerts') {
      sorted.sort((a, b) => (b.health?.alerts || 0) - (a.health?.alerts || 0));
    }
    return sorted;
  }, [monitors, sortOrder]);

  return (
    <div className="portfolio-page">
      <div className="page-header header-spacing">
        <div>
          <h1 className="page-title">Portfolio Heat-Map</h1>
          <p className="page-subtitle">Overview of all active models and their health statuses.</p>
        </div>
      </div>

      <div className="portfolio-kpi-row">
        <KPICard title="Total Models" value={kpis.total} />
        <KPICard title="Average Health" value={`${kpis.avgHealth}`} />
        <KPICard title="Critical Models" value={kpis.critical} status={kpis.critical > 0 ? "critical" : "healthy"} />
        <KPICard title="Healthy Models" value={kpis.healthy} />
      </div>

      <div className="portfolio-controls panel mb-4">
        <span className="mr-2 font-semibold">Sort By:</span>
        <button className={`btn btn-sm ${sortOrder === 'name' ? 'btn-primary' : 'btn-outline'} mr-2 pill-btn`} onClick={() => setSortOrder('name')}>Name</button>
        <button className={`btn btn-sm ${sortOrder === 'health' ? 'btn-primary' : 'btn-outline'} mr-2 pill-btn`} onClick={() => setSortOrder('health')}>Health</button>
        <button className={`btn btn-sm ${sortOrder === 'alerts' ? 'btn-primary' : 'btn-outline'} pill-btn`} onClick={() => setSortOrder('alerts')}>Alerts</button>
      </div>

      {loading ? (
        <div className="loading-state">Loading portfolio...</div>
      ) : (
        <div className="portfolio-grid">
          {sortedMonitors.map(m => {
            const score = m.health?.score || 0;
            let statusClass = 'healthy';
            if (score < 50) statusClass = 'critical';
            else if (score < 70) statusClass = 'warning';
            else if (score < 90) statusClass = 'watch'; // using watch for orange/yellow

            return (
              <div 
                key={m.monitor_id} 
                className={`portfolio-card ${statusClass} panel`}
                onClick={() => m.latestRun && navigate(`/runs?runId=${m.latestRun.run_id}`)}
              >
                <div className="portfolio-card-header">
                  <h3>{m.name}</h3>
                  {m.latestRun && <ArrowUpRight className="text-muted" size={16} />}
                </div>
                <div className="portfolio-card-body">
                  <div className="health-section">
                    <HealthGauge score={score} status={statusClass} size="sm" />
                  </div>
                  <div className="details-section">
                    {m.latestRun ? (
                      <>
                        <div className="mb-2">
                          <Badge status={m.health?.alerts > 0 ? 'warning' : 'healthy'}>
                            {m.health?.alerts || 0} Alerts
                          </Badge>
                        </div>
                        <div className="text-sm text-muted">
                          Last run: {new Date(m.latestRun.started_at).toLocaleDateString()}
                        </div>
                      </>
                    ) : (
                      <div className="text-sm text-muted">No runs available</div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Portfolio;

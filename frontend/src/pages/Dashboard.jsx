import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMonitors, getRuns, getRunHealth, getRunAlerts, getDatasets } from '../services/api';
import KPICard from '../components/ui/KPICard';
import HealthGauge from '../components/ui/HealthGauge';
import Badge from '../components/ui/Badge';
import AlertCard from '../components/ui/AlertCard';
import { useToast } from '../components/ui/ToastContext';
import { 
  Activity, 
  Database, 
  Shield, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle2,
  Upload,
  Plus,
  Loader2
} from 'lucide-react';
import './Dashboard.css';

const Dashboard = () => {
  const navigate = useNavigate();
  // Using destructuring based on the requested hook signature
  const toastCtx = useToast();
  const addToast = toastCtx ? toastCtx.addToast : () => {};
  
  const [loading, setLoading] = useState(true);
  const [monitors, setMonitors] = useState([]);
  const [runs, setRuns] = useState([]);
  const [datasetsCount, setDatasetsCount] = useState(0);
  const [latestRunsData, setLatestRunsData] = useState({}); // monitorId -> { run, health, alerts }
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [monitorsRes, runsRes, datasetsRes] = await Promise.all([
          getMonitors().catch(() => {
            addToast({ type: 'error', message: 'Failed to fetch monitors.' });
            return { data: [] };
          }),
          getRuns().catch(() => {
            addToast({ type: 'error', message: 'Failed to fetch runs.' });
            return { data: [] };
          }),
          getDatasets().catch(() => {
            return { data: [], total: 0 };
          })
        ]);
        
        const fetchedMonitors = monitorsRes.data || [];
        const fetchedRuns = runsRes.data || [];
        const totalDatasets = datasetsRes.total || (datasetsRes.data ? datasetsRes.data.length : 0);
        
        setMonitors(fetchedMonitors);
        setRuns(fetchedRuns);
        setDatasetsCount(totalDatasets);
        
        // Find latest run for each monitor
        const latestRunByMonitor = {};
        fetchedRuns.forEach(run => {
          const monitorId = run.monitor_id;
          if (!monitorId) return;
          
          if (!latestRunByMonitor[monitorId]) {
            latestRunByMonitor[monitorId] = run;
          } else {
            const currentLatest = new Date(latestRunByMonitor[monitorId].completed_at || latestRunByMonitor[monitorId].created_at || 0);
            const thisRunDate = new Date(run.completed_at || run.created_at || 0);
            if (thisRunDate > currentLatest) {
              latestRunByMonitor[monitorId] = run;
            }
          }
        });
        
        // Fetch health and alerts for those latest runs
        const runDataPromises = Object.values(latestRunByMonitor).map(async (run) => {
          try {
            const [healthRes, alertsRes] = await Promise.all([
              getRunHealth(run.run_id).catch(() => ({ data: { score: null } })),
              getRunAlerts(run.run_id).catch(() => ({ data: [] }))
            ]);
            
            return {
              monitorId: run.monitor_id,
              run,
              health: healthRes?.data?.score ?? null,
              alerts: alertsRes?.data || []
            };
          } catch (e) {
            return {
              monitorId: run.monitor_id,
              run,
              health: null,
              alerts: []
            };
          }
        });
        
        const runDataResults = await Promise.all(runDataPromises);
        const newLatestRunsData = {};
        runDataResults.forEach(data => {
          newLatestRunsData[data.monitorId] = data;
        });
        
        setLatestRunsData(newLatestRunsData);
      } catch (error) {
        console.error("Dashboard data load error:", error);
        addToast({ type: 'error', message: 'Failed to load dashboard data.' });
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, [addToast]);

  const { lastUpdated, avgHealth, totalAlerts, activeMonitors } = useMemo(() => {
    let latestTime = 0;
    let totalHealth = 0;
    let healthCount = 0;
    let alertCount = 0;
    
    Object.values(latestRunsData).forEach(({ run, health, alerts }) => {
      const runTime = new Date(run.completed_at || run.created_at || 0).getTime();
      if (runTime > latestTime) {
        latestTime = runTime;
      }
      
      if (health !== null) {
        totalHealth += health;
        healthCount++;
      }
      
      alertCount += alerts.length;
    });
    
    return {
      lastUpdated: latestTime > 0 ? new Date(latestTime).toLocaleString() : 'No recent runs',
      avgHealth: healthCount > 0 ? Math.round(totalHealth / healthCount) : 0,
      totalAlerts: alertCount,
      activeMonitors: monitors.length
    };
  }, [latestRunsData, monitors]);

  const sortedAlerts = useMemo(() => {
    const allAlerts = [];
    Object.values(latestRunsData).forEach(({ alerts }) => {
      if (alerts && Array.isArray(alerts)) {
        allAlerts.push(...alerts);
      }
    });
    
    // Sort by severity (critical first) then by time
    const severityWeight = { critical: 3, high: 2, medium: 1, low: 0 };
    return allAlerts.sort((a, b) => {
      const wA = severityWeight[a.severity?.toLowerCase()] ?? 0;
      const wB = severityWeight[b.severity?.toLowerCase()] ?? 0;
      if (wA !== wB) return wB - wA;
      
      const tA = new Date(a.created_at || 0).getTime();
      const tB = new Date(b.created_at || 0).getTime();
      return tB - tA;
    }).slice(0, 10);
  }, [latestRunsData]);

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spinner" size={24} />
        <span>Loading dashboard data...</span>
      </div>
    );
  }

  const getHealthStatus = (score) => {
    if (score === null || score === undefined) return 'unknown';
    if (score >= 90) return 'healthy';
    if (score >= 70) return 'watch';
    if (score >= 50) return 'warning';
    return 'critical';
  };

  return (
    <div className="dashboard-container">
      {/* Section 1: Page Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">Model Monitoring Dashboard</h1>
        <p className="dashboard-subtitle">Last updated: {lastUpdated}</p>
      </div>

      {/* Section 2: KPI Summary Row */}
      <div className="kpi-grid">
        <KPICard 
          title="Total Models" 
          value={datasetsCount || activeMonitors} 
          icon={Database} 
        />
        <KPICard 
          title="Active Monitors" 
          value={activeMonitors} 
          icon={Activity} 
        />
        <KPICard 
          title="Total Runs" 
          value={runs.length} 
          icon={BarChart3} 
        />
        <KPICard 
          title="Avg Health Score" 
          value={avgHealth ? `${avgHealth}%` : 'N/A'} 
          status={getHealthStatus(avgHealth)}
          icon={Shield} 
        />
      </div>

      {/* Section 3: Monitor Health Grid */}
      <div>
        <h2 className="section-title">Monitor Health</h2>
        {monitors.length === 0 ? (
          <div className="empty-state">
            <Activity size={48} />
            <div>
              <h3>No monitors found</h3>
              <p className="dashboard-subtitle">Create your first monitor to start tracking model health.</p>
            </div>
            <button className="empty-state-btn" onClick={() => navigate('/monitors')}>
              <Plus size={20} /> Create Monitor
            </button>
          </div>
        ) : (
          <div className="monitor-grid">
            {monitors.map(monitor => {
              const runData = latestRunsData[monitor.monitor_id];
              const healthScore = runData?.health;
              const alertsCount = runData?.alerts?.length || 0;
              const runDate = runData?.run 
                ? new Date(runData.run.completed_at || runData.run.created_at).toLocaleString() 
                : 'Never run';

              return (
                <div 
                  key={monitor.monitor_id} 
                  className="monitor-card"
                  onClick={() => navigate(runData?.run ? `/runs?runId=${runData.run.run_id}` : '/runs')}
                >
                  <div className="monitor-card-header">
                    <div>
                      <h3 className="monitor-name">{monitor.name || `Monitor ${monitor.monitor_id}`}</h3>
                      <div className="monitor-date">Last run: {runDate}</div>
                    </div>
                    {healthScore !== null && healthScore !== undefined ? (
                       <HealthGauge score={healthScore} status={getHealthStatus(healthScore)} size="sm" />
                    ) : (
                       <Badge status="info">No Data</Badge>
                    )}
                  </div>
                  <div className="monitor-card-body">
                    <div className="monitor-alerts">
                      <AlertTriangle size={16} className="icon-muted" />
                      <span className="alerts-label">Alerts</span>
                    </div>
                    <Badge status={alertsCount > 0 ? 'critical' : 'healthy'}>
                      {alertsCount} {alertsCount === 1 ? 'Alert' : 'Alerts'}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="dashboard-layout-bottom">
        {/* Section 4: Recent Alerts Feed */}
        <div>
          <h2 className="section-title">Recent Alerts</h2>
          {sortedAlerts.length === 0 ? (
            <div className="alerts-feed empty">
              <CheckCircle2 size={24} />
              <span>✓ All clear — no alerts across active monitors</span>
            </div>
          ) : (
            <div className="alerts-feed">
              {sortedAlerts.map((alert, i) => (
                <AlertCard key={alert.alert_id || i} alert={alert} />
              ))}
            </div>
          )}
        </div>

        {/* Section 5: Quick Actions */}
        <div>
          <h2 className="section-title">Quick Actions</h2>
          <div className="quick-actions-grid">
            <div className="action-card" onClick={() => navigate('/datasets')}>
              <div className="action-icon">
                <Upload size={20} />
              </div>
              <span>Upload Dataset</span>
            </div>
            <div className="action-card" onClick={() => navigate('/monitors')}>
              <div className="action-icon">
                <Plus size={20} />
              </div>
              <span>Create Monitor</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

import React, { useEffect, useState, useMemo } from 'react';
import KPICard from '../components/ui/KPICard';
import HealthGauge from '../components/ui/HealthGauge';
import Badge from '../components/ui/Badge';
import AlertCard from '../components/ui/AlertCard';
import DataTable from '../components/ui/DataTable';
import Tabs from '../components/ui/Tabs';
import Modal from '../components/ui/Modal';
import TimeSeriesTrendChart from '../components/ui/TimeSeriesTrendChart';
import CsiHistogramViewer from '../components/ui/CsiHistogramViewer';
import BarChart from '../components/ui/BarChart';
import LineChart from '../components/ui/LineChart';
import { useToast } from '../components/ui/ToastContext';
import { Clock, Calendar, Activity, ChevronDown, ChevronRight, RefreshCw, Trash2, Database, CheckCircle, AlertTriangle, Info, ActivitySquare, TrendingDown, PanelLeft } from 'lucide-react';

import {
  getRuns, getRun, getMonitors, deleteRun,
  getRunMetrics, getRunCharts, getChartImageUrl,
  getRunStatTests, getRunVintage, getRunOverrideAnalysis, 
  getRunFairness, getRunTimeSeries, getNarratives, generateNarrative, verifyNarrative,
  getRunHealth, getRunAlerts, getRunSegments, getRunInsights
} from '../services/api';
import './Runs.css';

const formatMetricKey = (key, displayName) => {
  if (displayName) return displayName;
  const mapping = {
    'psi_prediction_score': 'Score PSI',
    'perf_auc': 'ROC AUC',
    'calib_ratio_overall': 'Calibration Ratio',
    'approval_rate': 'Approval Rate',
    'bad_rate': 'Bad Rate',
    'perf_gini': 'Gini Coefficient'
  };
  if (mapping[key]) return mapping[key];
  return key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
};

const Runs = () => {
  const { addToast } = useToast();
  
  // List state
  const [runs, setRuns] = useState([]);
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState(null);

  // Detail state
  const [runDetails, setRunDetails] = useState(null);
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [narrative, setNarrative] = useState(null);
  const [insights, setInsights] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [activeTab, setActiveTab] = useState('metrics');
  const [detailLoading, setDetailLoading] = useState(false);
  const [narrativeGenerating, setNarrativeGenerating] = useState(false);

  // Lazy tabs state
  const [charts, setCharts] = useState(null);
  const [statTests, setStatTests] = useState(null);
  const [segments, setSegments] = useState(null);
  const [analyticsData, setAnalyticsData] = useState({ vintage: null, override: null, fairness: null, timeSeries: null });
  const [tabLoading, setTabLoading] = useState(false);

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Delete modal state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [runToDelete, setRunToDelete] = useState(null);

  // Expandable cards state
  const [expandedRootCauses, setExpandedRootCauses] = useState(false);
  const [expandedActions, setExpandedActions] = useState(false);

  // Citation state
  const [citationResult, setCitationResult] = useState(null);
  const [verifying, setVerifying] = useState(false);

  // Per-section generation state
  const [regeneratingSection, setRegeneratingSection] = useState(null);

  useEffect(() => {
    fetchRunsAndMonitors();
  }, []);

  const fetchRunsAndMonitors = async () => {
    setLoading(true);
    try {
      const [runsRes, monitorsRes] = await Promise.all([getRuns(), getMonitors()]);
      setRuns(runsRes.data || []);
      setMonitors(monitorsRes.data || []);
      if (runsRes.data && runsRes.data.length > 0 && !selectedRunId) {
        setSelectedRunId(runsRes.data[0].run_id);
      }
    } catch (e) {
      addToast({ message: 'Failed to load runs', type: 'error', duration: 5000 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedRunId) {
      fetchCoreRunDetails(selectedRunId);
      // Reset lazy loaded data
      setCharts(null);
      setStatTests(null);
      setSegments(null);
      setAnalyticsData({ vintage: null, override: null, fairness: null, timeSeries: null });
    }
  }, [selectedRunId]);

  useEffect(() => {
    if (selectedRunId && activeTab) {
      loadTabData(selectedRunId, activeTab);
    }
  }, [selectedRunId, activeTab]);

  const fetchCoreRunDetails = async (runId) => {
    setDetailLoading(true);
    try {
      const [runRes, healthRes, alertsRes, metricsRes, insightsRes] = await Promise.all([
        getRun(runId),
        getRunHealth(runId).catch(() => ({ data: { score: 0, status: 'unknown' }})),
        getRunAlerts(runId).catch(() => ({ data: [] })),
        getRunMetrics(runId).catch(() => ({ data: [] })),
        getRunInsights(runId).catch(() => ({ data: null }))
      ]);

      setRunDetails(runRes.data);
      setHealth(healthRes.data);
      setAlerts(alertsRes.data || []);
      setMetrics(metricsRes.data || []);
      setInsights(insightsRes.data);

      // Fetch narratives softly
      try {
        const nRes = await getNarratives(runId);
        setNarrative(nRes.data);
      } catch (e) {
        setNarrative(null);
      }
    } catch (e) {
      addToast({ message: 'Failed to load run details', type: 'error', duration: 5000 });
    } finally {
      setDetailLoading(false);
    }
  };

  const loadTabData = async (runId, tab) => {
    setTabLoading(true);
    try {
      if (tab === 'charts' && charts === null) {
        const res = await getRunCharts(runId);
        setCharts(res.data || []);
      } else if (tab === 'statistics' && statTests === null) {
        const res = await getRunStatTests(runId);
        setStatTests(res.data || { tests: [] });
      } else if (tab === 'segments' && segments === null) {
        const res = await getRunSegments(runId);
        setSegments(res.data || []);
      } else if (tab === 'analytics' && analyticsData.vintage === null) {
        const [vRes, oRes, fRes, tRes] = await Promise.allSettled([
          getRunVintage(runId),
          getRunOverrideAnalysis(runId),
          getRunFairness(runId),
          getRunTimeSeries(runId)
        ]);
        setAnalyticsData({
          vintage: vRes.status === 'fulfilled' ? vRes.value.data : null,
          override: oRes.status === 'fulfilled' ? oRes.value.data : null,
          fairness: fRes.status === 'fulfilled' ? fRes.value.data : null,
          timeSeries: tRes.status === 'fulfilled' ? tRes.value.data : null
        });
      }
    } catch (e) {
      addToast({ message: `Failed to load ${tab} data`, type: 'error', duration: 3000 });
    } finally {
      setTabLoading(false);
    }
  };

  const confirmDelete = (e, runId) => {
    e.stopPropagation();
    setRunToDelete(runId);
    setIsDeleteModalOpen(true);
  };

  const handleDeleteRun = async () => {
    try {
      await deleteRun(runToDelete);
      addToast({ message: 'Run deleted successfully', type: 'success', duration: 3000 });
      if (selectedRunId === runToDelete) setSelectedRunId(null);
      setIsDeleteModalOpen(false);
      setRunToDelete(null);
      fetchRunsAndMonitors();
    } catch (err) {
      addToast({ message: 'Failed to delete run', type: 'error', duration: 5000 });
    }
  };

  const handleGenerateNarrative = async (section = null) => {
    if (section) setRegeneratingSection(section);
    else setNarrativeGenerating(true);

    try {
      const res = await generateNarrative(selectedRunId, section);
      if (section) {
        setNarrative(prev => ({ ...prev, [section]: res.data[section] || prev[section] }));
      } else {
        setNarrative(res.data);
      }
      addToast({ message: `${section ? section + ' ' : ''}Narrative generated successfully`, type: 'success', duration: 3000 });
    } catch (e) {
      addToast({ message: `Failed to generate narrative${section ? ' for ' + section : ''}`, type: 'error', duration: 5000 });
    } finally {
      if (section) setRegeneratingSection(null);
      else setNarrativeGenerating(false);
    }
  };

  const handleVerifyCitations = async () => {
    setVerifying(true);
    try {
      const res = await verifyNarrative(selectedRunId);
      setCitationResult(res.data || res); // Depending on how verifyNarrative returns
    } catch (e) {
      addToast({ message: 'Failed to verify citations', type: 'error', duration: 5000 });
    } finally {
      setVerifying(false);
    }
  };

  // Safe renderer for narrative text
  const renderText = (val) => {
    if (Array.isArray(val)) return val.map((v, i) => <li key={i}>{String(v)}</li>);
    return <span>{val ? String(val) : ''}</span>;
  };

  const kpiMetrics = useMemo(() => {
    const kpiKeys = {
      'perf_auc': { name: 'ROC AUC', explanation: "Area Under ROC Curve. Measures the model's ability to distinguish good from bad loans. Higher is better." },
      'perf_gini': { name: 'Gini', explanation: "Measures the model's discriminatory power. Above 0.4 is good, above 0.6 is excellent." },
      'psi_prediction_score': { name: 'PSI', explanation: "Population Stability Index. Measures drift in score distribution. Below 0.1 is stable, above 0.25 is significant." },
      'calib_ratio_overall': { name: 'Calibration Ratio', explanation: "Ratio of actual default rate to predicted. Close to 1.0 means the model is well-calibrated." },
      'approval_rate': { name: 'Approval Rate', explanation: "Percentage of applications approved by the model's decision boundary." },
      'bad_rate': { name: 'Bad Rate', explanation: "Percentage of approved loans that defaulted. Lower is better." }
    };
    
    return Object.entries(kpiKeys).map(([key, info]) => {
      const metric = metrics.find(m => m.metric_key === key);
      return {
        key,
        title: info.name,
        explanation: info.explanation,
        value: metric ? (metric.scalar_value !== null ? metric.scalar_value.toFixed(4) : metric.scalar_label) : '-',
        status: metric ? (metric.status === 'skipped' ? 'skipped' : metric.threshold_breached ? 'critical' : 'healthy') : 'info',
        baseline: metric?.threshold_value
      };
    });
  }, [metrics]);

  const monitorName = useMemo(() => {
    if (!runDetails) return 'Unknown Monitor';
    const m = monitors.find(m => m.monitor_id === runDetails.monitor_id);
    return m ? m.name : 'Unknown Monitor';
  }, [runDetails, monitors]);

  // Tab Definitions
  const tabs = [
    { id: 'metrics', label: 'Metrics', icon: Activity },
    { id: 'charts', label: 'Charts', icon: ActivitySquare },
    { id: 'statistics', label: 'Statistics', icon: Info },
    { id: 'segments', label: 'Segments', icon: Database },
    { id: 'analytics', label: 'Analytics', icon: TrendingDown }
  ];

  return (
    <div className="runs-page">
      <div className="runs-layout">
        
        {/* LEFT COLUMN - Run History */}
        {isSidebarOpen ? (
          <div className="runs-sidebar panel">
            <div className="sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>Run History</h3>
              <button 
                className="btn btn-secondary" 
                onClick={() => setIsSidebarOpen(false)}
                title="Hide Sidebar"
                style={{ padding: '0.4rem', border: 'none', background: 'transparent' }}
              >
                <PanelLeft size={20} color="var(--text-secondary)" />
              </button>
            </div>
            <div className="run-list">
            {loading ? (
              <div className="loading-state">Loading runs...</div>
            ) : runs.length === 0 ? (
              <div className="empty-state">No runs found.</div>
            ) : (
              runs.map(run => {
                const mon = monitors.find(m => m.monitor_id === run.monitor_id);
                const mName = mon ? mon.name : 'Unknown';
                const isActive = selectedRunId === run.run_id;
                
                // Assuming status could be used as a simple health proxy for the list if health score not directly in list
                const statusColor = run.status === 'completed' ? 'healthy' : (run.status === 'failed' ? 'critical' : 'warning');
                
                return (
                  <div 
                    key={run.run_id} 
                    className={`run-list-item ${isActive ? 'active' : ''}`}
                    onClick={() => setSelectedRunId(run.run_id)}
                  >
                    <div className="run-item-content">
                      <div className="run-item-top">
                        <Badge status={statusColor} size="sm" className="status-dot" />
                        <span className="monitor-name">{mName}</span>
                      </div>
                      <div className="run-item-bottom">
                        <span className="run-id-short">{run.run_id.substring(0, 8)}</span>
                        <span className="run-date">{new Date(run.started_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button 
                      className="delete-btn" 
                      onClick={(e) => confirmDelete(e, run.run_id)}
                      title="Delete run"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
        ) : (
          <div className="runs-sidebar panel" style={{ width: '60px', alignItems: 'center', paddingTop: '1.25rem', borderRight: '1px solid var(--border-light)', flexShrink: 0 }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => setIsSidebarOpen(true)}
              title="Show Sidebar"
              style={{ padding: '0.4rem', border: 'none', background: 'transparent' }}
            >
              <PanelLeft size={20} color="var(--text-secondary)" />
            </button>
          </div>
        )}

        {/* RIGHT COLUMN - Run Detail */}
        <div className="runs-detail">
          {detailLoading ? (
            <div className="loading-state full-height">Loading run details...</div>
          ) : !runDetails ? (
            <div className="empty-state full-height">Select a run to view details</div>
          ) : (
            <div className="detail-scroll-container">
              
              {/* SECTION 1: Hero Banner */}
              <div className={`hero-banner ${health?.status || 'info'}`}>
                <div className="hero-content">
                  <div className="hero-health">
                    <HealthGauge score={health?.score || 0} status={health?.status || 'info'} size="lg" />
                  </div>
                  <div className="hero-info">
                    <div className="hero-status">
                      <h2>{health?.summary || (health?.status === 'healthy' ? 'Model is healthy — no critical issues detected' : 'Model requires attention')}</h2>
                    </div>
                    <div className="hero-meta">
                      <div className="meta-item"><Activity size={16}/> <span>{monitorName}</span></div>
                      <div className="meta-item"><Calendar size={16}/> <span>{new Date(runDetails.started_at).toLocaleString()}</span></div>
                      {runDetails.completed_at && (
                        <div className="meta-item"><Clock size={16}/> <span>{((new Date(runDetails.completed_at) - new Date(runDetails.started_at)) / 1000).toFixed(1)}s duration</span></div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* SECTION 2: Executive Summary */}
              <div className="executive-summary panel">
                <div className="panel-header-flex">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <h3>Executive Summary</h3>
                    {narrative && (
                      <button 
                        className="btn btn-outline btn-sm" 
                        onClick={() => handleGenerateNarrative('executive_summary')}
                        disabled={regeneratingSection === 'executive_summary'}
                        title="Regenerate this section"
                        style={{ border: 'none', padding: '0.25rem', color: 'var(--text-muted)' }}
                      >
                        <RefreshCw size={14} className={regeneratingSection === 'executive_summary' ? 'spin' : ''} />
                      </button>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      className="btn btn-outline btn-sm regenerate-btn" 
                      onClick={handleVerifyCitations}
                      disabled={verifying}
                    >
                      {verifying ? 'Verifying...' : 'Verify Citations'}
                    </button>
                    <button 
                      className="btn btn-outline btn-sm regenerate-btn" 
                      onClick={() => handleGenerateNarrative()}
                      disabled={narrativeGenerating}
                    >
                      <RefreshCw size={14} className={narrativeGenerating ? 'spin' : ''} />
                      {narrativeGenerating ? 'Generating...' : 'Regenerate All'}
                    </button>
                  </div>
                </div>
                
                {narrative ? (
                  <div className="narrative-content">
                    {narrative.executive_summary && <p className="lead-text">{narrative.executive_summary}</p>}
                    
                    {citationResult && (
                      <div className="citation-badge-container mb-4">
                        {citationResult.status === 'passed' && <Badge status="healthy">✓ All {citationResult.total_citations ?? citationResult.total} citations verified</Badge>}
                        {citationResult.status === 'warning' && <Badge status="warning">⚠ {citationResult.unverified_count} of {citationResult.total_citations ?? citationResult.total} citations unverified</Badge>}
                        {citationResult.status === 'failed' && <Badge status="critical">✗ {citationResult.unverified_count} citations could not be verified</Badge>}
                      </div>
                    )}

                    <div className="narrative-cards">
                      {narrative.technical_summary && (
                         <div className="expandable-card">
                          <div className="expand-header" onClick={() => {}}>
                            <div className="expand-title">
                              <span>Technical Summary</span>
                              <button 
                                className="btn btn-outline btn-sm" 
                                onClick={(e) => { e.stopPropagation(); handleGenerateNarrative('technical_summary'); }}
                                disabled={regeneratingSection === 'technical_summary'}
                                style={{ border: 'none', padding: '0.25rem', color: 'var(--text-muted)' }}
                              >
                                <RefreshCw size={14} className={regeneratingSection === 'technical_summary' ? 'spin' : ''} />
                              </button>
                            </div>
                          </div>
                          <div className="expand-content" style={{ display: 'block' }}>
                            <p>{narrative.technical_summary}</p>
                          </div>
                         </div>
                      )}
                      
                      {narrative.root_causes && narrative.root_causes.length > 0 && (
                        <div className="expandable-card">
                          <div className="expand-header" onClick={() => setExpandedRootCauses(!expandedRootCauses)}>
                            <div className="expand-title">
                              <AlertTriangle size={18} className="text-warning"/> 
                              <span>Root Causes ({narrative.root_causes.length})</span>
                              <button 
                                className="btn btn-outline btn-sm" 
                                onClick={(e) => { e.stopPropagation(); handleGenerateNarrative('root_causes'); }}
                                disabled={regeneratingSection === 'root_causes'}
                                style={{ border: 'none', padding: '0.25rem', color: 'var(--text-muted)' }}
                              >
                                <RefreshCw size={14} className={regeneratingSection === 'root_causes' ? 'spin' : ''} />
                              </button>
                            </div>
                            {expandedRootCauses ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                          </div>
                          {expandedRootCauses && (
                            <div className="expand-content">
                              <ul>{renderText(narrative.root_causes)}</ul>
                            </div>
                          )}
                        </div>
                      )}

                      {narrative.recommended_actions && narrative.recommended_actions.length > 0 && (
                        <div className="expandable-card">
                          <div className="expand-header" onClick={() => setExpandedActions(!expandedActions)}>
                            <div className="expand-title">
                              <CheckCircle size={18} className="text-success"/> 
                              <span>Recommended Actions ({narrative.recommended_actions.length})</span>
                              <button 
                                className="btn btn-outline btn-sm" 
                                onClick={(e) => { e.stopPropagation(); handleGenerateNarrative('recommended_actions'); }}
                                disabled={regeneratingSection === 'recommended_actions'}
                                style={{ border: 'none', padding: '0.25rem', color: 'var(--text-muted)' }}
                              >
                                <RefreshCw size={14} className={regeneratingSection === 'recommended_actions' ? 'spin' : ''} />
                              </button>
                            </div>
                            {expandedActions ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                          </div>
                          {expandedActions && (
                            <div className="expand-content">
                              <ul>{renderText(narrative.recommended_actions)}</ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <p>No AI narrative generated for this run yet.</p>
                  </div>
                )}

                {insights && insights.deterministic_findings?.length > 0 && (
                  <div className="insights-summary panel">
                    <h4 className="insights-title">Key Insights</h4>
                    <ul className="insights-list">
                      {insights.deterministic_findings.map((finding, i) => (
                        <li key={finding.finding_id || i}>
                          <strong>{finding.title}:</strong> {finding.narrative}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* SECTION 3: KPI Row */}
              <div className="kpi-row">
                {kpiMetrics.map((kpi, idx) => (
                  <KPICard 
                    key={idx}
                    title={kpi.title}
                    value={kpi.value}
                    status={kpi.status}
                    baseline={kpi.baseline !== undefined ? `Thr: ${kpi.baseline}` : null}
                    explanation={kpi.explanation}
                  />
                ))}
              </div>

              {/* SECTION 4: Alerts Panel */}
              <div className="alerts-panel panel">
                <h3>Active Alerts</h3>
                <div className="alerts-list">
                  {alerts && alerts.length > 0 ? (
                    [...alerts].sort((a,b) => a.severity === 'critical' ? -1 : 1).map((alert, idx) => (
                      <AlertCard key={alert.alert_id || idx} alert={alert} />
                    ))
                  ) : (
                    <div className="no-alerts-banner">
                      <CheckCircle size={20} />
                      <span>No alerts triggered — all metrics within thresholds</span>
                    </div>
                  )}
                </div>
              </div>

              {/* SECTION 5: Detail Tabs */}
              <div className="detail-tabs panel">
                <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
                
                <div className="tab-content-container">
                  {tabLoading && activeTab !== 'metrics' ? (
                    <div className="loading-state">Loading data...</div>
                  ) : (
                    <>
                      {/* METRICS TAB */}
                      {activeTab === 'metrics' && (
                        <div className="metrics-tab">
                          {Object.entries(metrics.reduce((acc, m) => {
                            if (!acc[m.category]) acc[m.category] = [];
                            acc[m.category].push(m);
                            return acc;
                          }, {})).map(([category, catMetrics]) => {
                            const cols = [
                              { key: 'name', label: 'Metric' },
                              { key: 'status', label: 'Status' },
                              { key: 'value', label: 'Value', align: 'right' },
                              { key: 'threshold', label: 'Threshold', align: 'right' }
                            ];
                            const data = catMetrics.map(m => ({
                              name: formatMetricKey(m.metric_key, m.display_name),
                              status: <Badge status={m.status === 'skipped' ? 'skipped' : m.status === 'error' ? 'error' : m.threshold_breached ? 'critical' : 'healthy'} size="sm">
                                {m.status === 'skipped' ? 'SKIPPED' : m.status === 'error' ? 'ERROR' : m.threshold_breached ? 'BREACHED' : 'OK'}
                              </Badge>,
                              value: m.status === 'skipped' ? '-' : m.scalar_value !== null ? m.scalar_value.toFixed(4) : m.scalar_label || '-',
                              threshold: m.threshold_value !== null ? m.threshold_value : '-'
                            }));
                            return (
                              <div key={category} className="metrics-category">
                                <h4>{category.replace('_', ' ').toUpperCase()}</h4>
                                <DataTable columns={cols} data={data} emptyMessage="No metrics in this category" compact />
                              </div>
                            );
                          })}

                          {metrics.filter(m => m.metric_key === 'csi_feature_drift' && m.table_data).map((driftMetric, idx) => (
                            <div key={`drift-${idx}`} className="metrics-category mt-4">
                              <h4>FEATURE DRIFT (CSI)</h4>
                              <CsiHistogramViewer featureData={driftMetric.table_data} />
                              <DataTable 
                                columns={[
                                  { key: 'feature', label: 'Feature' },
                                  { key: 'csi_value', label: 'CSI Value', align: 'right' },
                                  { key: 'status', label: 'Status' }
                                ]}
                                data={[...(driftMetric.table_data || [])].sort((a,b) => (b.csi_value || 0) - (a.csi_value || 0)).map(row => ({
                                  feature: row.feature,
                                  csi_value: row.csi_value?.toFixed(4) || '-',
                                  status: <Badge status={row.status === 'ok' ? 'healthy' : (row.status === 'warning' ? 'warning' : 'critical')} size="sm">
                                    {row.status ? row.status.toUpperCase() : 'UNKNOWN'}
                                  </Badge>
                                }))}
                                compact
                              />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* CHARTS TAB */}
                      {activeTab === 'charts' && (
                        <div className="charts-grid">
                          {charts?.map(c => (
                            <div key={c.chart_id} className="chart-card panel">
                              <h4>{c.title}</h4>
                              {c.subtitle && <p className="chart-subtitle">{c.subtitle}</p>}
                              {c.chart_type === 'bar' || c.chart_type === 'histogram' ? (
                                <BarChart series={c.series} xLabel={c.x_label} yLabel={c.y_label} annotations={c.annotations || []} />
                              ) : c.chart_type === 'line' ? (
                                <LineChart series={c.series} xLabel={c.x_label} yLabel={c.y_label} annotations={c.annotations || []} />
                              ) : (
                                <div className="chart-image-container">
                                  <img
                                    src={getChartImageUrl(selectedRunId, c.chart_id, 'svg')}
                                    alt={c.title}
                                    onError={(e) => { e.target.src = getChartImageUrl(selectedRunId, c.chart_id, 'png') }}
                                  />
                                </div>
                              )}
                            </div>
                          ))}
                          {(!charts || charts.length === 0) && <div className="empty-state">No charts generated for this run.</div>}
                        </div>
                      )}

                      {/* STATISTICS TAB */}
                      {activeTab === 'statistics' && (
                        <div className="stats-tab">
                          <DataTable 
                            columns={[
                              { key: 'test_name', label: 'Test Name' },
                              { key: 'statistic', label: 'Statistic', align: 'right' },
                              { key: 'p_value', label: 'P-Value', align: 'right' },
                              { key: 'conclusion', label: 'Conclusion' },
                              { key: 'result', label: 'Result' }
                            ]}
                            data={(statTests?.tests || []).map(t => ({
                              test_name: t.test_name,
                              statistic: t.statistic?.toFixed(4) || '-',
                              p_value: t.p_value !== null ? (t.p_value < 0.0001 ? '<0.0001' : t.p_value.toFixed(4)) : '-',
                              conclusion: t.conclusion,
                              result: <Badge status={t.pass_fail === 'fail' ? 'critical' : 'healthy'} size="sm">{t.pass_fail.toUpperCase()}</Badge>
                            }))}
                            emptyMessage="No statistical tests found."
                          />
                        </div>
                      )}

                      {/* SEGMENTS TAB */}
                      {activeTab === 'segments' && (
                        <div className="segments-tab">
                           <DataTable
                            columns={[
                              { key: 'segment_column', label: 'Segment' },
                              { key: 'segment_value', label: 'Value' },
                              { key: 'count', label: 'Count', align: 'right' },
                              { key: 'share_pct', label: 'Share', align: 'right' },
                              { key: 'bad_rate', label: 'Bad Rate', align: 'right' },
                              { key: 'share_drift', label: 'Share Drift', align: 'right' },
                              { key: 'status', label: 'Status' }
                            ]}
                            data={(segments || []).map(s => ({
                              segment_column: s.segment_column,
                              segment_value: s.segment_value,
                              count: s.count,
                              share_pct: s.share_pct !== null && s.share_pct !== undefined ? `${(s.share_pct * 100).toFixed(1)}%` : '-',
                              bad_rate: s.bad_rate !== null && s.bad_rate !== undefined ? `${(s.bad_rate * 100).toFixed(2)}%` : '-',
                              share_drift: s.share_drift !== null && s.share_drift !== undefined ? `${s.share_drift >= 0 ? '+' : ''}${(s.share_drift * 100).toFixed(2)}pp` : '-',
                              status: <Badge status={s.drift_status === 'alert' ? 'critical' : (s.drift_status === 'watch' ? 'watch' : 'healthy')} size="sm">
                                {s.drift_status ? s.drift_status.toUpperCase() : 'N/A'}
                              </Badge>
                            }))}
                            emptyMessage="No segment breakdowns available. Select segment columns when creating the monitor to enable this view."
                          />
                        </div>
                      )}

                      {/* ANALYTICS TAB */}
                      {activeTab === 'analytics' && (
                        <div className="analytics-tab">
                          {analyticsData.vintage && analyticsData.vintage.roll_rate_matrix && (
                            <div className="analytics-section">
                              <h4>Vintage Analysis (Roll Rate)</h4>
                              <p className="analytics-note">{analyticsData.vintage.roll_rate_matrix.note}</p>
                              <DataTable 
                                columns={[
                                  { key: 'bucket', label: 'Bucket' },
                                  { key: 'count', label: 'Count', align: 'right' },
                                  { key: 'pct', label: 'Percentage', align: 'right' },
                                  { key: 'cum_pct', label: 'Cumulative %', align: 'right' }
                                ]}
                                data={analyticsData.vintage.roll_rate_matrix.buckets.map(b => ({
                                  bucket: b.bucket,
                                  count: b.count,
                                  pct: `${b.pct.toFixed(2)}%`,
                                  cum_pct: `${b.cumulative_pct.toFixed(2)}%`
                                }))}
                                compact
                              />
                              <div className="analytics-summary highlight-info">
                                <strong>Severe Delinquency Rate:</strong> {(analyticsData.vintage.roll_rate_matrix.severe_delinquency_rate * 100).toFixed(2)}%
                              </div>
                            </div>
                          )}

                          {analyticsData.override && (
                            <div className="analytics-section">
                              <h4>Override Analysis</h4>
                              <p className="analytics-note italic">"{analyticsData.override.insight_narrative}"</p>
                              <div className="override-grid">
                                <div className="override-stat">
                                  <div className="stat-label">Model Declines</div>
                                  <div className="stat-val">{analyticsData.override.total_model_declines}</div>
                                </div>
                                <div className="override-stat">
                                  <div className="stat-label">Overrides</div>
                                  <div className="stat-val text-warning">{analyticsData.override.positive_override_count}</div>
                                </div>
                                <div className="override-stat">
                                  <div className="stat-label">Override Rate</div>
                                  <div className="stat-val">{(analyticsData.override.positive_override_rate * 100).toFixed(1)}%</div>
                                </div>
                                <div className="override-stat">
                                  <div className="stat-label">Override Bad Rate</div>
                                  <div className="stat-val text-error">{(analyticsData.override.positive_override_bad_rate * 100).toFixed(1)}%</div>
                                </div>
                              </div>
                              <div className={`analytics-summary ${analyticsData.override.override_performing_better ? 'highlight-success' : 'highlight-error'}`}>
                                <strong>Conclusion:</strong> {analyticsData.override.override_performing_better ? 'Overrides are performing better or equal to model approvals.' : 'Overrides are performing worse than standard model approvals.'}
                              </div>
                            </div>
                          )}

                          {analyticsData.fairness && analyticsData.fairness.di_results && (
                            <div className="analytics-section">
                              <h4>Fairness Analysis (Disparate Impact)</h4>
                              <div className="fairness-header">
                                <p className="analytics-note">{analyticsData.fairness.regulatory_note}</p>
                                <strong>Approval Rate: {(analyticsData.fairness.overall_approval_rate * 100).toFixed(1)}%</strong>
                              </div>
                              <DataTable 
                                columns={[
                                  { key: 'group_col', label: 'Group Column' },
                                  { key: 'group_value', label: 'Group Value' },
                                  { key: 'n', label: 'N', align: 'right' },
                                  { key: 'approval', label: 'Approval Rate', align: 'right' },
                                  { key: 'di', label: 'DI Ratio', align: 'right' },
                                  { key: 'status', label: 'Status' }
                                ]}
                                data={analyticsData.fairness.di_results.map(r => ({
                                  group_col: r.group_col,
                                  group_value: r.group_value,
                                  n: r.n,
                                  approval: `${(r.approval_rate * 100).toFixed(1)}%`,
                                  di: r.di_ratio.toFixed(2),
                                  status: <Badge status={r.status === 'ok' ? 'healthy' : 'critical'} size="sm">{r.status.toUpperCase()}</Badge>
                                }))}
                                compact
                              />
                              <div className="analytics-summary highlight-info mt-3">
                                <strong>Summary:</strong> {analyticsData.fairness.ecoa_compliance_summary}
                              </div>
                            </div>
                          )}

                           {analyticsData.timeSeries && analyticsData.timeSeries.available && (
                            <div className="analytics-card panel">
                              <h4>Time-Series Cohort Trends</h4>
                              <p className="analytics-note">{analyticsData.timeSeries.trend_summary}</p>
                              {analyticsData.timeSeries.periods && analyticsData.timeSeries.periods.length > 0 && (
                                <>
                                  <TimeSeriesTrendChart periods={analyticsData.timeSeries.periods} />
                                  <DataTable
                                    columns={[
                                      { key: 'period', label: 'Cohort Period' },
                                      { key: 'volume', label: 'Volume' },
                                      { key: 'default_rate', label: 'Default Rate', render: r => r.default_rate !== undefined ? `${(r.default_rate * 100).toFixed(2)}%` : 'N/A' },
                                      { key: 'mean_score', label: 'Mean Score', render: r => r.mean_score !== undefined ? r.mean_score : 'N/A' },
                                      { key: 'approval_rate', label: 'Approval Rate', render: r => r.approval_rate !== undefined ? `${(r.approval_rate * 100).toFixed(1)}%` : 'N/A' }
                                    ]}
                                    data={analyticsData.timeSeries.periods}
                                    emptyMessage="No time-series periods computed."
                                    compact
                                  />
                                </>
                              )}
                            </div>
                          )}

                          {!analyticsData.vintage && !analyticsData.override && !analyticsData.fairness && !analyticsData.timeSeries?.available && (
                            <div className="empty-state">No analytics data available for this run.</div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

            </div>
          )}
        </div>
      </div>

      <Modal 
        isOpen={isDeleteModalOpen} 
        onClose={() => setIsDeleteModalOpen(false)} 
        onConfirm={handleDeleteRun}
        title="Delete Run"
        variant="danger"
        confirmText="Delete"
        cancelText="Cancel"
      >
        <p>Are you sure you want to delete this run and all its artifacts? This action cannot be undone.</p>
      </Modal>

    </div>
  );
};

export default Runs;

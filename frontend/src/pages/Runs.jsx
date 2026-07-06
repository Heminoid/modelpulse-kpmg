import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { 
  getRuns, getRun, getRunMetrics, getRunCharts, getChartImageUrl, getRunStatTests, 
  getRunVintage, getRunOverrideAnalysis, getRunFairness, getRunTimeSeries,
  generateNarrative, getNarratives, getMonitors, deleteRun
} from '../services/api';
import { PlayCircle, BarChart2, Activity, Cpu, Bot, CheckCircle, Trash2, RefreshCw } from 'lucide-react';
import './Runs.css';

const Runs = () => {
  const [runs, setRuns] = useState([]);
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState(null);

  // Detail States
  const [runDetails, setRunDetails] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // overview, metrics, charts, stats, analytics
  const [detailLoading, setDetailLoading] = useState(false);

  // Sub-data states
  const [metrics, setMetrics] = useState([]);
  const [charts, setCharts] = useState([]);
  const [statTests, setStatTests] = useState(null);
  const [narrative, setNarrative] = useState(null);
  const [narrativeGenerating, setNarrativeGenerating] = useState(false);

  // Analytics states
  const [analyticsData, setAnalyticsData] = useState({ vintage: null, override: null, fairness: null, timeseries: null });

  useEffect(() => {
    fetchRunsAndMonitors();
  }, []);

  const fetchRunsAndMonitors = async () => {
    setLoading(true);
    try {
      const [runsRes, monitorsRes] = await Promise.all([
        getRuns(),
        getMonitors()
      ]);
      setRuns(runsRes.data || []);
      setMonitors(monitorsRes.data || []);
      if (runsRes.data && runsRes.data.length > 0 && !selectedRunId) {
        setSelectedRunId(runsRes.data[0].run_id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetails(selectedRunId);
    }
  }, [selectedRunId]);

  const fetchRunDetails = async (runId) => {
    setDetailLoading(true);
    setActiveTab('overview');
    try {
      const runRes = await getRun(runId);
      setRunDetails(runRes.data);
      
      // Fetch narrative if exists
      try {
        const nRes = await getNarratives(runId);
        setNarrative(nRes.data);
      } catch (e) {
        setNarrative(null); // No narrative yet
      }

      // Pre-fetch metrics
      try {
        const mRes = await getRunMetrics(runId);
        setMetrics(mRes.data || []);
      } catch (e) { setMetrics([]); }

      // Pre-fetch charts
      const cRes = await getRunCharts(runId);
      setCharts(cRes.data || []);

      // Pre-fetch stat tests
      try {
        const sRes = await getRunStatTests(runId);
        setStatTests(sRes.data);
      } catch (e) { setStatTests(null); }

      // Pre-fetch analytics
      try {
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
          timeseries: tRes.status === 'fulfilled' ? tRes.value.data : null
        });
      } catch (e) {}

    } catch (e) {
      console.error(e);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDeleteRun = async (e, runId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this run and all its artifacts?")) return;
    try {
      await deleteRun(runId);
      if (selectedRunId === runId) setSelectedRunId(null);
      await fetchRunsAndMonitors();
    } catch (err) {
      alert("Failed to delete run");
    }
  };

  const handleGenerateNarrative = async () => {
    setNarrativeGenerating(true);
    try {
      const res = await generateNarrative(selectedRunId);
      setNarrative(res.data);
    } catch (e) {
      alert("Failed to generate narrative");
    } finally {
      setNarrativeGenerating(false);
    }
  };

  const safeRenderString = (val) => {
    if (typeof val === 'string') return val;
    if (val === null || val === undefined) return '';
    return JSON.stringify(val, null, 2);
  };

  const renderOverview = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <Card title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span><Bot size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }}/> AI Narrative Analysis</span>
          {narrative && (
            <button 
              className="btn btn-secondary" 
              style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              onClick={handleGenerateNarrative} 
              disabled={narrativeGenerating}
            >
              <RefreshCw size={14} className={narrativeGenerating ? 'spin' : ''} />
              {narrativeGenerating ? 'Regenerating...' : 'Regenerate Analysis'}
            </button>
          )}
        </div>
      }>
        {narrative ? (
          <div className="narrative-content">
            {narrative.executive_summary && (
              <>
                <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Executive Summary</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', whiteSpace: 'pre-wrap' }}>{safeRenderString(narrative.executive_summary)}</p>
              </>
            )}
            {narrative.technical_summary && (
              <>
                <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Technical Summary</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', whiteSpace: 'pre-wrap' }}>{safeRenderString(narrative.technical_summary)}</p>
              </>
            )}
            {narrative.root_causes && narrative.root_causes.length > 0 && (
              <>
                <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Root Causes</h3>
                <ul style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', paddingLeft: '1.5rem' }}>
                  {Array.isArray(narrative.root_causes) ? 
                    narrative.root_causes.map((rc, i) => <li key={i}>{safeRenderString(rc)}</li>) : 
                    <li>{safeRenderString(narrative.root_causes)}</li>}
                </ul>
              </>
            )}
            {narrative.recommended_actions && narrative.recommended_actions.length > 0 && (
              <>
                <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Recommended Actions</h3>
                <ul style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', paddingLeft: '1.5rem' }}>
                  {Array.isArray(narrative.recommended_actions) ? 
                    narrative.recommended_actions.map((ra, i) => <li key={i}>{safeRenderString(ra)}</li>) :
                    <li>{safeRenderString(narrative.recommended_actions)}</li>}
                </ul>
              </>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>No AI narrative generated for this run yet.</p>
            <button className="btn btn-primary" onClick={handleGenerateNarrative} disabled={narrativeGenerating}>
              {narrativeGenerating ? 'Generating...' : 'Generate Narrative'}
            </button>
          </div>
        )}
      </Card>

      <Card title="Run Status">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <CheckCircle color="var(--success)" size={24} />
          <div>
            <h3 style={{ color: 'var(--success)' }}>{runDetails?.status?.toUpperCase()}</h3>
            <p style={{ color: 'var(--text-muted)' }}>Completed at {new Date(runDetails?.completed_at).toLocaleString()}</p>
          </div>
        </div>
      </Card>
    </div>
  );

  const renderMetrics = () => {
    if (!metrics || metrics.length === 0) return <p>No metrics found for this run.</p>;
    
    // Group metrics by category
    const grouped = metrics.reduce((acc, curr) => {
      if (!acc[curr.category]) acc[curr.category] = [];
      acc[curr.category].push(curr);
      return acc;
    }, {});

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {Object.entries(grouped).map(([category, catMetrics]) => (
          <Card key={category} title={category.replace('_', ' ').toUpperCase()}>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric Name</th>
                    <th>Status</th>
                    <th>Value</th>
                    <th>Threshold</th>
                  </tr>
                </thead>
                <tbody>
                  {catMetrics.map((m, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{m.display_name || m.metric_key}</td>
                      <td>
                        {m.status === 'skipped' ? (
                          <span style={{ color: 'var(--warning)', fontWeight: 'bold' }}>SKIPPED</span>
                        ) : m.status === 'error' ? (
                          <span style={{ color: 'var(--error)', fontWeight: 'bold' }}>ERROR</span>
                        ) : m.threshold_breached ? (
                          <span style={{ color: 'var(--error)', fontWeight: 'bold' }}>BREACHED</span>
                        ) : (
                          <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>OK</span>
                        )}
                      </td>
                      <td>
                        {m.status === 'skipped' ? (
                          <span style={{ color: 'var(--text-muted)' }}>{m.skipped_reason || 'N/A'}</span>
                        ) : m.scalar_value !== null ? (
                          m.scalar_value.toFixed(4)
                        ) : m.scalar_label ? (
                          m.scalar_label
                        ) : (
                          '-'
                        )}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{m.threshold_value !== null ? m.threshold_value : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>
    );
  };

  const renderCharts = () => (
    <div className="charts-grid">
      {charts.map(c => (
        <Card key={c.chart_id} title={c.title} subtitle={c.subtitle}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
            <img 
              src={getChartImageUrl(selectedRunId, c.chart_id, 'svg')} 
              alt={c.title} 
              style={{ maxWidth: '100%', height: 'auto', maxHeight: '400px' }} 
              onError={(e) => { e.target.src = getChartImageUrl(selectedRunId, c.chart_id, 'png') }}
            />
          </div>
        </Card>
      ))}
      {charts.length === 0 && <p>No charts generated for this run.</p>}
    </div>
  );

  const renderStatTests = () => {
    if (!statTests || !statTests.tests || statTests.tests.length === 0) return <p>No statistical tests found.</p>;
    
    return (
      <Card title="Statistical Tests">
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Test Name</th>
                <th>Statistic</th>
                <th>P-Value</th>
                <th>Alpha</th>
                <th>Conclusion</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {statTests.tests.map((test, index) => (
                <tr key={index}>
                  <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{test.test_name}</td>
                  <td>{test.statistic?.toFixed(4) || '-'}</td>
                  <td>
                    {test.p_value !== null ? 
                      (test.p_value < 0.0001 ? '<0.0001' : test.p_value.toFixed(4)) 
                      : '-'}
                  </td>
                  <td>{test.alpha || '-'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{test.conclusion}</td>
                  <td>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                      fontWeight: 'bold',
                      textTransform: 'uppercase',
                      background: test.pass_fail === 'fail' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)',
                      color: test.pass_fail === 'fail' ? 'var(--error)' : 'var(--success)'
                    }}>
                      {test.pass_fail}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    );
  };

  const renderAnalytics = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* VINTAGE ANALYSIS */}
      <Card title="Vintage Analysis (Roll Rate)">
        {analyticsData.vintage && analyticsData.vintage.roll_rate_matrix ? (
          <div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              {analyticsData.vintage.roll_rate_matrix.note}
            </p>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Bucket</th>
                    <th>Count</th>
                    <th>Percentage</th>
                    <th>Cumulative %</th>
                  </tr>
                </thead>
                <tbody>
                  {analyticsData.vintage.roll_rate_matrix.buckets.map((b, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: '500' }}>{b.bucket}</td>
                      <td>{b.count}</td>
                      <td>{b.pct.toFixed(2)}%</td>
                      <td>{b.cumulative_pct.toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
              <strong>Severe Delinquency Rate:</strong> {(analyticsData.vintage.roll_rate_matrix.severe_delinquency_rate * 100).toFixed(2)}%
            </div>
          </div>
        ) : (
          <p>No vintage data available</p>
        )}
      </Card>

      {/* OVERRIDE ANALYSIS */}
      <Card title="Override Analysis (Score Cutoff: 600)">
        {analyticsData.override ? (
          <div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontStyle: 'italic' }}>
              "{analyticsData.override.insight_narrative}"
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Model Declines (Total)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{analyticsData.override.total_model_declines}</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Overrides (Approved)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--warning)' }}>{analyticsData.override.positive_override_count}</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Override Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{(analyticsData.override.positive_override_rate * 100).toFixed(1)}%</div>
              </div>
              <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Override Bad Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--error)' }}>{(analyticsData.override.positive_override_bad_rate * 100).toFixed(1)}%</div>
              </div>
            </div>
            
            <div style={{ padding: '1rem', background: analyticsData.override.override_performing_better ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)' }}>
              <strong>Conclusion:</strong> {analyticsData.override.override_performing_better ? 'Overrides are performing better or equal to model approvals.' : 'Overrides are performing worse than standard model approvals.'}
            </div>
          </div>
        ) : (
          <p>No override analysis available</p>
        )}
      </Card>

      {/* FAIRNESS ANALYSIS */}
      <Card title="Fairness Analysis (Disparate Impact)">
        {analyticsData.fairness ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <p style={{ color: 'var(--text-secondary)' }}>{analyticsData.fairness.regulatory_note}</p>
              <div style={{ fontWeight: '500' }}>Overall Approval Rate: {(analyticsData.fairness.overall_approval_rate * 100).toFixed(1)}%</div>
            </div>
            
            {analyticsData.fairness.di_results && analyticsData.fairness.di_results.length > 0 ? (
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Group Column</th>
                      <th>Group Value</th>
                      <th>N</th>
                      <th>Approval Rate</th>
                      <th>DI Ratio</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.fairness.di_results.map((r, i) => (
                      <tr key={i}>
                        <td style={{ color: 'var(--text-secondary)' }}>{r.group_col}</td>
                        <td style={{ fontWeight: '500' }}>{r.group_value}</td>
                        <td>{r.n}</td>
                        <td>{(r.approval_rate * 100).toFixed(1)}%</td>
                        <td>{r.di_ratio.toFixed(2)}</td>
                        <td>
                          <span style={{
                            padding: '0.25rem 0.5rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', fontWeight: 'bold', textTransform: 'uppercase',
                            background: r.status === 'ok' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: r.status === 'ok' ? 'var(--success)' : 'var(--error)'
                          }}>
                            {r.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No disparate impact tests performed.</p>
            )}
            
            <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: 'var(--radius-md)' }}>
              <strong>Summary:</strong> {analyticsData.fairness.ecoa_compliance_summary}
            </div>
          </div>
        ) : (
          <p>No fairness data available</p>
        )}
      </Card>
    </div>
  );

  return (
    <div className="runs-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">Monitor Runs</h1>
          <p className="page-subtitle">Detailed execution history and deep analytics.</p>
        </div>
      </div>

      <div className="runs-layout">
        <div className="runs-sidebar glass-panel">
          <h3 style={{ padding: '1.5rem 1.5rem 0.5rem', margin: 0, color: 'var(--text-secondary)' }}>History</h3>
          {loading ? (
            <div style={{ padding: '1.5rem' }}>Loading...</div>
          ) : (
            <ul className="run-list">
              {runs.map(run => {
                const monitor = monitors.find(m => m.monitor_id === run.monitor_id);
                const monitorName = monitor ? monitor.name : 'Unknown Monitor';
                return (
                  <li 
                    key={run.run_id} 
                    className={`run-list-item ${selectedRunId === run.run_id ? 'active' : ''}`}
                    onClick={() => setSelectedRunId(run.run_id)}
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <PlayCircle size={18} color={selectedRunId === run.run_id ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                      <div>
                        <div className="run-id" style={{ fontWeight: '500' }}>{monitorName}</div>
                        <div className="run-date">
                          {run.run_id.substring(0, 8)} • {new Date(run.started_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <button 
                      className="btn-icon" 
                      onClick={(e) => handleDeleteRun(e, run.run_id)}
                      title="Delete run"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
                    >
                      <Trash2 size={16} color="var(--error)" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="run-detail">
          {detailLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>Loading run details...</div>
          ) : !selectedRunId ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>Select a run to view details</div>
          ) : (
            <>
              <div className="tabs" style={{ display: 'flex', gap: '2rem', borderBottom: '1px solid var(--border-light)', marginBottom: '2rem' }}>
                {['overview', 'metrics', 'charts', 'stats', 'analytics'].map(tab => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    style={{ 
                      background: 'none', border: 'none', padding: '1rem 0', color: activeTab === tab ? 'var(--accent-primary)' : 'var(--text-muted)', 
                      fontWeight: activeTab === tab ? 600 : 400, cursor: 'pointer', borderBottom: activeTab === tab ? '2px solid var(--accent-primary)' : '2px solid transparent',
                      textTransform: 'capitalize', fontSize: '1rem'
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              <div className="tab-content">
                {activeTab === 'overview' && renderOverview()}
                {activeTab === 'metrics' && renderMetrics()}
                {activeTab === 'charts' && renderCharts()}
                {activeTab === 'stats' && renderStatTests()}
                {activeTab === 'analytics' && renderAnalytics()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Runs;

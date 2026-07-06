import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getMonitors, createMonitor, triggerRun, getDatasets, getMapping } from '../services/api';
import { Activity, Plus, Play, Server, ArrowLeft } from 'lucide-react';

const Monitors = () => {
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [runningMonitorId, setRunningMonitorId] = useState(null);

  // Form State
  const [datasets, setDatasets] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    baseline_dataset_id: '',
    dataset_id: '',
    model_id: '',
    schedule_cron: ''
  });

  const fetchMonitors = async () => {
    setLoading(true);
    try {
      const res = await getMonitors();
      setMonitors(res.data || []);
    } catch (error) {
      console.error("Failed to load monitors", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDatasetsList = async () => {
    try {
      const res = await getDatasets(1, 100);
      setDatasets(res.data || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchMonitors();
    fetchDatasetsList();
  }, []);

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    try {
      // Fetch mapping for the target dataset to include in payload
      const mappingRes = await getMapping(formData.dataset_id);
      if (!mappingRes.data) {
        alert("Target dataset must have a saved mapping before creating a monitor.");
        return;
      }
      
      const payload = {
        name: formData.name,
        dataset_id: formData.dataset_id,
        baseline_dataset_id: formData.baseline_dataset_id || null,
        schedule_cron: formData.schedule_cron || null,
        model_id: formData.model_id || null,
        column_mapping: mappingRes.data
      };
      
      if (!payload.baseline_dataset_id) delete payload.baseline_dataset_id;
      if (!payload.schedule_cron) delete payload.schedule_cron;
      if (!payload.model_id) delete payload.model_id;

      await createMonitor(payload);
      setIsCreating(false);
      fetchMonitors();
    } catch (error) {
      console.error("Failed to create monitor", error);
      alert("Failed to create monitor. Ensure dataset has mapping.");
    }
  };

  const handleTriggerRun = async (monitorId) => {
    setRunningMonitorId(monitorId);
    try {
      await triggerRun(monitorId);
      alert('Run triggered successfully!');
    } catch (error) {
      console.error("Trigger failed", error);
      alert('Failed to trigger run.');
    } finally {
      setRunningMonitorId(null);
    }
  };

  if (isCreating) {
    return (
      <div className="monitors-container">
        <div className="page-header" style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button className="btn btn-secondary" style={{ padding: '0.5rem' }} onClick={() => setIsCreating(false)}>
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="page-title">Create Monitor</h1>
              <p className="page-subtitle">Configure a new model monitoring pipeline.</p>
            </div>
          </div>
        </div>

        <Card style={{ maxWidth: '600px', margin: '0 auto' }}>
          <form onSubmit={handleCreateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Monitor Name</label>
              <input 
                required
                type="text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                placeholder="e.g., Credit Risk Production Monitor"
              />
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Baseline Dataset</label>
              <select 
                value={formData.baseline_dataset_id}
                onChange={e => setFormData({...formData, baseline_dataset_id: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
              >
                <option value="">Select a dataset... (Optional)</option>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Target Dataset (Current Data)</label>
              <select 
                required
                value={formData.dataset_id}
                onChange={e => setFormData({...formData, dataset_id: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
              >
                <option value="">Select a dataset...</option>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Model ID (Optional)</label>
              <input 
                type="text" 
                value={formData.model_id}
                onChange={e => setFormData({...formData, model_id: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                placeholder="e.g., model-v1.0"
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Schedule (Cron)</label>
              <input 
                type="text" 
                value={formData.schedule_cron}
                onChange={e => setFormData({...formData, schedule_cron: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                placeholder="e.g., 0 0 * * * (Daily)"
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setIsCreating(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Create Monitor</button>
            </div>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="monitors-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">Monitors</h1>
          <p className="page-subtitle">Configure and manage data drift and performance monitors.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsCreating(true)}>
          <Plus size={18} /> New Monitor
        </button>
      </div>

      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading monitors...</div>
        ) : monitors.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <Activity size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No monitors configured</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Create a monitor to start tracking data drift and performance.</p>
            <button className="btn btn-primary" onClick={() => setIsCreating(true)}><Plus size={18} /> New Monitor</button>
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Baseline</th>
                  <th>Target</th>
                  <th>Schedule</th>
                  <th>Created At</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {monitors.map((monitor) => (
                  <tr key={monitor.monitor_id}>
                    <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Server size={16} color="var(--accent-primary)" />
                        {monitor.name || 'Unnamed Monitor'}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {datasets.find(d => d.id === monitor.baseline_dataset_id)?.filename || monitor.baseline_dataset_id?.substring(0,8) || 'None'}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {datasets.find(d => d.id === monitor.dataset_id)?.filename || monitor.dataset_id?.substring(0,8) || 'Unknown'}
                    </td>
                    <td>{monitor.schedule_cron || '-'}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{new Date(monitor.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button 
                        className="btn btn-primary" 
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                        onClick={() => handleTriggerRun(monitor.monitor_id)}
                        disabled={runningMonitorId === monitor.monitor_id}
                      >
                        {runningMonitorId === monitor.monitor_id ? 'Triggering...' : <><Play size={14} /> Run Now</>}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default Monitors;

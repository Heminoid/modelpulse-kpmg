import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getMonitors, createMonitor, triggerRun, getDatasets, getMapping } from '../services/api';
import { Activity, Plus, Play, Server } from 'lucide-react';
import { useToast } from '../components/ui/ToastContext';
import Modal from '../components/ui/Modal';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import './Monitors.css';

const Monitors = () => {
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [runningMonitorId, setRunningMonitorId] = useState(null);
  
  const { addToast } = useToast();

  // Form State
  const [datasets, setDatasets] = useState([]);
  const [availableSegmentFields, setAvailableSegmentFields] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    baseline_dataset_id: '',
    dataset_id: '',
    model_id: '',
    schedule_cron: '',
    selected_segments: []
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

  useEffect(() => {
    if (!formData.dataset_id) {
      setAvailableSegmentFields([]);
      return;
    }
    let cancelled = false;
    getMapping(formData.dataset_id)
      .then(res => {
        if (!cancelled) setAvailableSegmentFields(res.data?.segment_fields || []);
      })
      .catch(() => {
        if (!cancelled) setAvailableSegmentFields([]);
      });
    return () => { cancelled = true; };
  }, [formData.dataset_id]);

  const toggleSegmentField = (col) => {
    setFormData(prev => ({
      ...prev,
      selected_segments: prev.selected_segments.includes(col)
        ? prev.selected_segments.filter(c => c !== col)
        : [...prev.selected_segments, col]
    }));
  };

  const handleCreateSubmit = async () => {
    try {
      // Fetch mapping for the target dataset to include in payload
      const mappingRes = await getMapping(formData.dataset_id);
      if (!mappingRes.data) {
        addToast({ message: 'Target dataset must have a saved mapping before creating a monitor.', type: 'warning' });
        return;
      }
      
      const payload = {
        name: formData.name,
        dataset_id: formData.dataset_id,
        baseline_dataset_id: formData.baseline_dataset_id || null,
        schedule_cron: formData.schedule_cron || null,
        model_id: formData.model_id || null,
        column_mapping: mappingRes.data,
        selected_segments: formData.selected_segments
      };

      if (!payload.baseline_dataset_id) delete payload.baseline_dataset_id;
      if (!payload.schedule_cron) delete payload.schedule_cron;
      if (!payload.model_id) delete payload.model_id;
      if (!payload.selected_segments.length) delete payload.selected_segments;

      await createMonitor(payload);
      setIsCreating(false);
      addToast({ message: 'Monitor created successfully', type: 'success' });
      fetchMonitors();
    } catch (error) {
      console.error("Failed to create monitor", error);
      addToast({ message: 'Failed to create monitor. Ensure dataset has mapping.', type: 'error' });
    }
  };

  const handleTriggerRun = async (monitorId) => {
    setRunningMonitorId(monitorId);
    try {
      await triggerRun(monitorId);
      addToast({ message: 'Run triggered successfully!', type: 'success' });
    } catch (error) {
      console.error("Trigger failed", error);
      addToast({ message: 'Failed to trigger run.', type: 'error' });
    } finally {
      setRunningMonitorId(null);
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: (row) => (
        <div className="monitor-name-cell">
          <Server size={16} className="text-accent" />
          <span className="font-medium text-primary">{row.name || 'Unnamed Monitor'}</span>
        </div>
      )
    },
    {
      key: 'baseline',
      label: 'Baseline',
      render: (row) => (
        <span className="text-muted">
          {datasets.find(d => d.id === row.baseline_dataset_id)?.filename || row.baseline_dataset_id?.substring(0,8) || 'None'}
        </span>
      )
    },
    {
      key: 'target',
      label: 'Target',
      render: (row) => (
        <span className="text-muted">
          {datasets.find(d => d.id === row.dataset_id)?.filename || row.dataset_id?.substring(0,8) || 'Unknown'}
        </span>
      )
    },
    {
      key: 'schedule',
      label: 'Schedule',
      render: (row) => row.schedule_cron || '-'
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <Badge status="info">Active</Badge> // Mocking status
    },
    {
      key: 'created',
      label: 'Created At',
      render: (row) => (
        <span className="text-muted">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      )
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (row) => (
        <button 
          className="btn btn-primary run-btn" 
          onClick={() => handleTriggerRun(row.monitor_id)}
          disabled={runningMonitorId === row.monitor_id}
        >
          {runningMonitorId === row.monitor_id ? 'Triggering...' : <><Play size={14} /> Run Now</>}
        </button>
      )
    }
  ];

  return (
    <div className="monitors-container">
      <div className="page-header header-spacing">
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
          <div className="loading-state">Loading monitors...</div>
        ) : monitors.length === 0 ? (
          <div className="empty-state">
            <Activity size={48} className="empty-icon" />
            <h3 className="empty-title">No monitors configured</h3>
            <p className="empty-subtitle">Create a monitor to start tracking data drift and performance.</p>
            <button className="btn btn-primary" onClick={() => setIsCreating(true)}>
              <Plus size={18} /> New Monitor
            </button>
          </div>
        ) : (
          <DataTable 
            columns={columns}
            data={monitors}
            emptyMessage="No monitors found."
          />
        )}
      </Card>

      <Modal
        isOpen={isCreating}
        onClose={() => setIsCreating(false)}
        onConfirm={handleCreateSubmit}
        title="Create Monitor"
        confirmText="Create Monitor"
      >
        <div className="form-layout">
          <div className="form-group">
            <label className="form-label" htmlFor="monitor-name">Monitor Name</label>
            <input
              id="monitor-name"
              required
              type="text"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              className="form-input"
              placeholder="e.g., Credit Risk Production Monitor"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="monitor-baseline">Baseline Dataset</label>
            <select
              id="monitor-baseline"
              value={formData.baseline_dataset_id}
              onChange={e => setFormData({...formData, baseline_dataset_id: e.target.value})}
              className="form-input"
            >
              <option value="">Select a dataset... (Optional)</option>
              {datasets.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="monitor-target">Target Dataset (Current Data)</label>
            <select
              id="monitor-target"
              required
              value={formData.dataset_id}
              onChange={e => setFormData({...formData, dataset_id: e.target.value, selected_segments: []})}
              className="form-input"
            >
              <option value="">Select a dataset...</option>
              {datasets.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </div>

          {availableSegmentFields.length > 0 && (
            <fieldset className="form-group">
              <legend className="form-label">Segment Breakdown Columns (Optional)</legend>
              <div className="segment-checkbox-list">
                {availableSegmentFields.map(col => (
                  <label key={col} className="segment-checkbox-item" htmlFor={`segment-${col}`}>
                    <input
                      id={`segment-${col}`}
                      type="checkbox"
                      checked={formData.selected_segments.includes(col)}
                      onChange={() => toggleSegmentField(col)}
                    />
                    {col}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="monitor-model">Model ID (Optional)</label>
            <input
              id="monitor-model"
              type="text"
              value={formData.model_id}
              onChange={e => setFormData({...formData, model_id: e.target.value})}
              className="form-input"
              placeholder="e.g., model-v1.0"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="monitor-cron">Schedule (Cron)</label>
            <input
              id="monitor-cron"
              type="text"
              value={formData.schedule_cron}
              onChange={e => setFormData({...formData, schedule_cron: e.target.value})}
              className="form-input"
              placeholder="e.g., 0 0 * * * (Daily)"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Monitors;

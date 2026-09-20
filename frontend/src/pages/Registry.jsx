import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getModels, createModel, getChampionChallenger, updateModel } from '../services/api';
import { Box, Trophy, ShieldCheck, ShieldAlert } from 'lucide-react';
import { useToast } from '../components/ui/ToastContext';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import './Registry.css';

const Registry = () => {
  const [models, setModels] = useState([]);
  const [champion, setChampion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState(null);
  
  const { addToast } = useToast();
  
  // Register Form
  const [showRegister, setShowRegister] = useState(false);
  const [formData, setFormData] = useState({
    model_id: '',
    name: '',
    version: '1.0.0',
    stage: 'development',
    model_type: 'scorecard',
    owner: 'Data Science Team'
  });

  // Details Modal
  const [selectedModel, setSelectedModel] = useState(null);

  const fetchRegistryData = async () => {
    setLoading(true);
    try {
      const res = await getModels(1, 100);
      setModels(res.data || []);
      
      const champ = res.data?.find(m => m.stage === 'production');
      setChampion(champ);

      if (champ) {
        // Find a challenger (staging)
        const chall = res.data?.find(m => m.stage === 'staging');
        if (chall) {
          const compRes = await getChampionChallenger(champ.model_id, chall.model_id, true);
          setComparison(compRes.data);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistryData();
  }, []);

  const handleRegister = async () => {
    try {
      await createModel(formData);
      setShowRegister(false);
      addToast({ message: 'Model registered successfully', type: 'success' });
      fetchRegistryData();
    } catch (e) {
      addToast({ message: 'Failed to register model', type: 'error' });
    }
  };

  const handleStageChange = async (modelId, newStage) => {
    try {
      await updateModel(modelId, { stage: newStage });
      addToast({ message: 'Model stage updated', type: 'success' });
      fetchRegistryData();
    } catch (e) {
      addToast({ message: 'Failed to update stage', type: 'error' });
    }
  };

  const getStageBadgeStatus = (stage) => {
    switch (stage) {
      case 'development': return 'info';
      case 'staging': return 'watch';
      case 'production': return 'healthy';
      case 'archived':
      case 'retired': return 'deteriorating';
      default: return 'info';
    }
  };

  const renderComparison = () => {
    if (!comparison) return null;

    const { metric_deltas, metric_winners, champion_latest_metrics, challenger_latest_metrics } = comparison;
    const metrics = Object.keys(metric_winners);

    const compColumns = [
      { key: 'metric', label: 'Metric', render: row => row },
      { key: 'champion', label: `Champion (${comparison.champion_model_id})`, render: row => champion_latest_metrics[row]?.toFixed(4) || '-' },
      { key: 'challenger', label: `Challenger (${comparison.challenger_model_id})`, render: row => challenger_latest_metrics[row]?.toFixed(4) || '-' },
      { 
        key: 'delta', 
        label: 'Delta', 
        render: row => {
          const val = metric_deltas[row];
          return (
            <span className={val > 0 ? 'text-success' : 'text-error'}>
              {val > 0 ? '+' : ''}{val?.toFixed(4) || '-'}
            </span>
          );
        } 
      },
      {
        key: 'winner',
        label: 'Winner',
        render: row => {
          const winner = metric_winners[row];
          let colorClass = 'text-muted';
          if (winner === 'champion') colorClass = 'text-secondary';
          else if (winner === 'challenger') colorClass = 'text-success';
          return <span className={colorClass}>{winner.toUpperCase()}</span>;
        }
      }
    ];

    return (
      <Card title="Champion vs Challenger" icon={Trophy} className="mb-4">
        <p className="comparison-summary">{comparison.summary}</p>
        
        <div className="recommendation-box mb-4">
          {comparison.recommendation.includes('outperforms') ? (
            <ShieldAlert className="icon-warning" />
          ) : (
            <ShieldCheck className="icon-success" />
          )}
          <strong className="text-primary">Recommendation: {comparison.recommendation}</strong>
        </div>

        {comparison.ai_narrative && (
          <div className="ai-narrative-panel panel mb-4" style={{ backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: '8px' }}>
            <p className="lead-text" style={{ marginBottom: '1rem' }}>{comparison.ai_narrative.comparison_summary}</p>
            
            <h5 style={{ marginBottom: '0.5rem' }}>Key Differences</h5>
            <ul style={{ marginBottom: '1rem', paddingLeft: '1.5rem' }}>
              {comparison.ai_narrative.key_differences?.map((diff, i) => <li key={i}>{diff}</li>)}
            </ul>

            <h5 style={{ marginBottom: '0.5rem' }}>Risks</h5>
            <ul style={{ marginBottom: '1rem', paddingLeft: '1.5rem', color: 'var(--text-warning)' }}>
              {comparison.ai_narrative.risks?.map((risk, i) => <li key={i}><ShieldAlert size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }}/>{risk}</li>)}
            </ul>

            <Badge status="info">Recommendation: {comparison.ai_narrative.recommendation}</Badge>
          </div>
        )}

        <DataTable columns={compColumns} data={metrics} />
      </Card>
    );
  };

  const modelColumns = [
    { key: 'model_id', label: 'Model ID' },
    { key: 'name', label: 'Name' },
    { key: 'version', label: 'Version' },
    { 
      key: 'stage', 
      label: 'Stage',
      render: row => (
        <select
          className="stage-select"
          value={row.stage}
          onChange={(e) => handleStageChange(row.model_id, e.target.value)}
          aria-label={`Change stage for ${row.name || row.model_id}`}
        >
          <option value="development">Development</option>
          <option value="staging">Staging (Challenger)</option>
          <option value="production">Production (Champion)</option>
          <option value="archived">Archived</option>
          <option value="retired">Retired</option>
        </select>
      )
    },
    { 
      key: 'badge', 
      label: 'Status',
      render: row => <Badge status={getStageBadgeStatus(row.stage)}>{row.stage}</Badge>
    },
    { key: 'created_at', label: 'Registered At', render: row => new Date(row.created_at).toLocaleDateString() },
    { 
      key: 'actions', 
      label: 'Actions',
      render: row => (
        <button className="btn btn-secondary action-btn" onClick={() => setSelectedModel(row)}>
          View Details
        </button>
      )
    }
  ];

  return (
    <div className="registry-container">
      <div className="page-header header-spacing">
        <div>
          <h1 className="page-title">Model Registry</h1>
          <p className="page-subtitle">Govern model lifecycles and evaluate challengers.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowRegister(true)}>Register Model</button>
      </div>

      {renderComparison()}

      <Card title="Registered Models" icon={Box}>
        {loading ? (
          <div>Loading models...</div>
        ) : (
          <DataTable columns={modelColumns} data={models} emptyMessage="No models registered." />
        )}
      </Card>

      <Modal
        isOpen={showRegister}
        onClose={() => setShowRegister(false)}
        onConfirm={handleRegister}
        title="Register New Model"
        confirmText="Save"
      >
        <div className="form-layout">
          <div className="form-group">
            <label htmlFor="registry-model-id">Model ID</label>
            <input id="registry-model-id" required value={formData.model_id} onChange={e => setFormData({...formData, model_id: e.target.value})} className="form-input" />
          </div>
          <div className="form-group">
            <label htmlFor="registry-name">Name</label>
            <input id="registry-name" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="form-input" />
          </div>
          <div className="form-group">
            <label htmlFor="registry-version">Version</label>
            <input id="registry-version" required value={formData.version} onChange={e => setFormData({...formData, version: e.target.value})} className="form-input" />
          </div>
          <div className="form-group-flex">
            <div className="form-group">
              <label htmlFor="registry-type">Type</label>
              <input id="registry-type" required placeholder="Type" value={formData.model_type} onChange={e => setFormData({...formData, model_type: e.target.value})} className="form-input" />
            </div>
            <div className="form-group">
              <label htmlFor="registry-owner">Owner</label>
              <input id="registry-owner" required placeholder="Owner" value={formData.owner} onChange={e => setFormData({...formData, owner: e.target.value})} className="form-input" />
            </div>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={!!selectedModel}
        onClose={() => setSelectedModel(null)}
        onConfirm={() => setSelectedModel(null)}
        title="Model Details"
        confirmText="Close"
        cancelText=""
      >
        {selectedModel && (
          <div className="details-layout">
            <p><strong>Model ID:</strong> {selectedModel.model_id}</p>
            <p><strong>Name:</strong> {selectedModel.name}</p>
            <p><strong>Version:</strong> {selectedModel.version}</p>
            <p>
              <strong>Stage:</strong> 
              <Badge status={getStageBadgeStatus(selectedModel.stage)} className="ml-2">{selectedModel.stage}</Badge>
            </p>
            <p><strong>Description:</strong> {selectedModel.description || 'No description available.'}</p>
            <p><strong>Owner:</strong> {selectedModel.owner || 'Unknown'}</p>
            <p><strong>Registration Date:</strong> {new Date(selectedModel.created_at).toLocaleString()}</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Registry;

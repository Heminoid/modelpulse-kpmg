import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getModels, createModel, getChampionChallenger, updateModel } from '../services/api';
import { Box, Trophy, ArrowRight, ShieldCheck, ShieldAlert } from 'lucide-react';

const Registry = () => {
  const [models, setModels] = useState([]);
  const [champion, setChampion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState(null);
  
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
          const compRes = await getChampionChallenger(champ.model_id, chall.model_id);
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

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await createModel(formData);
      setShowRegister(false);
      fetchRegistryData();
    } catch (e) {
      alert("Failed to register model");
    }
  };

  const handleStageChange = async (modelId, newStage) => {
    try {
      await updateModel(modelId, { stage: newStage });
      fetchRegistryData();
    } catch (e) {
      alert("Failed to update stage");
    }
  };

  const renderComparison = () => {
    if (!comparison) return null;

    const { metric_deltas, metric_winners, champion_latest_metrics, challenger_latest_metrics } = comparison;
    const metrics = Object.keys(metric_winners);

    return (
      <Card title="Champion vs Challenger" icon={Trophy} className="mb-4">
        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>{comparison.summary}</p>
        
        <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {comparison.recommendation.includes('outperforms') ? (
            <ShieldAlert color="var(--warning)" />
          ) : (
            <ShieldCheck color="var(--success)" />
          )}
          <strong style={{ color: 'var(--text-primary)' }}>Recommendation: {comparison.recommendation}</strong>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Champion ({comparison.champion_model_id})</th>
                <th>Challenger ({comparison.challenger_model_id})</th>
                <th>Delta</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map(k => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{champion_latest_metrics[k]?.toFixed(4) || '-'}</td>
                  <td>{challenger_latest_metrics[k]?.toFixed(4) || '-'}</td>
                  <td style={{ color: metric_deltas[k] > 0 ? 'var(--success)' : 'var(--error)' }}>
                    {metric_deltas[k] > 0 ? '+' : ''}{metric_deltas[k]?.toFixed(4) || '-'}
                  </td>
                  <td style={{ 
                    color: metric_winners[k] === 'champion' ? 'var(--text-secondary)' : 
                           metric_winners[k] === 'challenger' ? 'var(--success)' : 'var(--text-muted)' 
                  }}>
                    {metric_winners[k].toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    );
  };

  return (
    <div className="registry-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">Model Registry</h1>
          <p className="page-subtitle">Govern model lifecycles and evaluate challengers.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowRegister(true)}>Register Model</button>
      </div>

      {showRegister && (
        <Card title="Register New Model" style={{ marginBottom: '2rem' }}>
          <form onSubmit={handleRegister} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label>Model ID</label>
              <input required value={formData.model_id} onChange={e => setFormData({...formData, model_id: e.target.value})} style={{ padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }} />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label>Name</label>
              <input required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} style={{ padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }} />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label>Version</label>
              <input required value={formData.version} onChange={e => setFormData({...formData, version: e.target.value})} style={{ padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }} />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label>Type & Owner</label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input required placeholder="Type" value={formData.model_type} onChange={e => setFormData({...formData, model_type: e.target.value})} style={{ flex: 1, padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }} />
                <input required placeholder="Owner" value={formData.owner} onChange={e => setFormData({...formData, owner: e.target.value})} style={{ flex: 1, padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowRegister(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Save</button>
            </div>
          </form>
        </Card>
      )}

      {renderComparison()}

      <Card title="Registered Models" icon={Box}>
        {loading ? (
          <div>Loading models...</div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Model ID</th>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Stage</th>
                  <th>Registered At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {models.map(model => (
                  <tr key={model.model_id}>
                    <td>{model.model_id}</td>
                    <td>{model.name}</td>
                    <td>{model.version}</td>
                    <td>
                      <select 
                        value={model.stage}
                        onChange={(e) => handleStageChange(model.model_id, e.target.value)}
                        style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}
                      >
                        <option value="development">Development</option>
                        <option value="staging">Staging (Challenger)</option>
                        <option value="production">Production (Champion)</option>
                        <option value="archived">Archived</option>
                      </select>
                    </td>
                    <td>{new Date(model.created_at).toLocaleDateString()}</td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem' }}>View Details</button>
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

export default Registry;

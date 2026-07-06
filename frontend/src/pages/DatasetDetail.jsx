import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css'; // We'll customize this for dark mode

import { 
  getDataset, 
  getDatasetProfile, 
  getDatasetPreview, 
  suggestMapping, 
  saveMapping, 
  getMapping, 
  validateMapping 
} from '../services/api';
import Card from '../components/Card';
import { ArrowLeft, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import './DatasetDetail.css';

const DatasetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [dataset, setDataset] = useState(null);
  const [activeTab, setActiveTab] = useState('preview'); // preview, profile, mapping
  const [loading, setLoading] = useState(true);

  // Tab Data
  const [previewData, setPreviewData] = useState([]);
  const [profileData, setProfileData] = useState(null);
  const [mappingData, setMappingData] = useState(null);
  
  // Mapping States
  const [columnMappings, setColumnMappings] = useState({});
  const [mappingValidation, setMappingValidation] = useState(null);

  useEffect(() => {
    const fetchBase = async () => {
      try {
        const res = await getDataset(id);
        setDataset(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchBase();
  }, [id]);

  useEffect(() => {
    const fetchTabData = async () => {
      setLoading(true);
      try {
        if (activeTab === 'preview') {
          if (previewData.length === 0) {
            const res = await getDatasetPreview(id);
            setPreviewData(res.data || []);
          }
        } else if (activeTab === 'profile') {
          if (!profileData) {
            const res = await getDatasetProfile(id);
            setProfileData(res.data);
          }
        } else if (activeTab === 'mapping') {
          if (!profileData) {
            const pRes = await getDatasetProfile(id);
            setProfileData(pRes.data);
          }
          if (!mappingData) {
            try {
              const mRes = await getMapping(id);
              if (mRes.data) {
                setMappingData(mRes.data);
                setColumnMappings(mRes.data.mappings || {});
              }
            } catch (e) {
              // no mapping
            }
          }
        }
      } catch (e) {
        console.error(`Failed fetching ${activeTab} data`, e);
      } finally {
        setLoading(false);
      }
    };
    fetchTabData();
  }, [activeTab, id]);

  const handleSuggestMapping = async () => {
    try {
      const res = await suggestMapping(id);
      if (res.data && res.data.suggestions) {
        const newMappings = {};
        res.data.suggestions.forEach(s => {
          newMappings[s.column_name] = s.suggested_role;
        });
        setColumnMappings(newMappings);
      }
    } catch (e) {
      alert('Failed to get mapping suggestions');
    }
  };

  const handleSaveMapping = async () => {
    try {
      const finalMappings = { ...columnMappings };
      if (profileData?.columns) {
        profileData.columns.forEach(col => {
          if (!finalMappings[col.name]) {
            finalMappings[col.name] = 'feature_field';
          }
        });
      }
      
      await saveMapping(id, { column_roles: finalMappings });
      alert('Mapping saved successfully');
      
      // Validate right after saving
      const vRes = await validateMapping(id);
      setMappingValidation(vRes.data);
    } catch (e) {
      alert('Failed to save mapping');
    }
  };

  const renderPreview = () => {
    if (loading) return <div>Loading preview...</div>;
    if (!previewData || previewData.length === 0) return <div>No preview data</div>;

    const columnDefs = Object.keys(previewData[0]).map(key => ({
      field: key,
      filter: true,
      sortable: true
    }));

    return (
      <div className="ag-theme-alpine-dark" style={{ height: '600px', width: '100%' }}>
        <AgGridReact
          rowData={previewData}
          columnDefs={columnDefs}
          pagination={true}
          paginationPageSize={20}
        />
      </div>
    );
  };

  const renderProfile = () => {
    if (loading) return <div>Loading profile...</div>;
    if (!profileData) return <div>No profile data</div>;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <Card title="Summary">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <div>
              <p style={{ color: 'var(--text-muted)' }}>Row Count</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{profileData.row_count}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)' }}>Column Count</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{profileData.column_count}</p>
            </div>
            <div>
              <p style={{ color: 'var(--text-muted)' }}>Duplicate Rows</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{profileData.duplicate_row_count}</p>
            </div>
          </div>
        </Card>
        
        <Card title="Column Profiles">
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Inferred Type</th>
                  <th>Null Count</th>
                  <th>Unique Count</th>
                </tr>
              </thead>
              <tbody>
                {profileData.columns?.map((col, idx) => (
                  <tr key={idx}>
                    <td>{col.name}</td>
                    <td>{col.inferred_type}</td>
                    <td>{col.null_count} ({(col.null_percent * 100).toFixed(1)}%)</td>
                    <td>{col.unique_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  };

  const renderMapping = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <h3 style={{ marginBottom: '0.5rem' }}>Column Mapping</h3>
              <p style={{ color: 'var(--text-muted)' }}>Map your dataset columns to logical roles for model monitoring.</p>
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button className="btn btn-secondary" onClick={handleSuggestMapping}>Auto-Suggest</button>
              <button className="btn btn-primary" onClick={handleSaveMapping}>Save Mapping</button>
            </div>
          </div>

          {mappingValidation && (
            <div style={{ padding: '1rem', background: mappingValidation.is_valid ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderLeft: `4px solid ${mappingValidation.is_valid ? 'var(--success)' : 'var(--error)'}`, marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                {mappingValidation.is_valid ? <CheckCircle size={18} color="var(--success)"/> : <AlertTriangle size={18} color="var(--error)"/>}
                <strong style={{ color: mappingValidation.is_valid ? 'var(--success)' : 'var(--error)' }}>
                  {mappingValidation.is_valid ? 'Mapping is Valid' : 'Mapping Validation Failed'}
                </strong>
              </div>
              {mappingValidation.errors && mappingValidation.errors.length > 0 && (
                <ul style={{ paddingLeft: '2rem', color: 'var(--error)' }}>
                  {mappingValidation.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
          )}

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {profileData?.columns?.map((col) => (
                  <tr key={col.name}>
                    <td>{col.name}</td>
                    <td>
                      <select 
                        value={columnMappings[col.name] || 'feature_field'}
                        onChange={(e) => setColumnMappings({ ...columnMappings, [col.name]: e.target.value })}
                        style={{ padding: '0.5rem', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', width: '200px' }}
                      >
                        <option value="feature_field">Feature</option>
                        <option value="target">Target</option>
                        <option value="prediction_score">Prediction Score</option>
                        <option value="prediction_probability">Prediction Probability</option>
                        <option value="decision">Decision</option>
                        <option value="dpd_field">DPD Field</option>
                        <option value="amount_field">Amount Field</option>
                        <option value="score_band">Score Band</option>
                        <option value="risk_band">Risk Band</option>
                        <option value="segment_field">Segment Field</option>
                        <option value="event_time">Event Time</option>
                        <option value="record_id">Record ID</option>
                        <option value="ignored">Ignore</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  };

  return (
    <div className="dataset-detail-container">
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn btn-secondary" style={{ padding: '0.5rem' }} onClick={() => navigate('/datasets')}>
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="page-title">{dataset?.filename || 'Loading Dataset...'}</h1>
            <p className="page-subtitle">ID: {id}</p>
          </div>
        </div>
      </div>

      <div className="tabs" style={{ display: 'flex', gap: '2rem', borderBottom: '1px solid var(--border-light)', marginBottom: '2rem' }}>
        {['preview', 'profile', 'mapping'].map(tab => (
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
        {activeTab === 'preview' && renderPreview()}
        {activeTab === 'profile' && renderProfile()}
        {activeTab === 'mapping' && renderMapping()}
      </div>
    </div>
  );
};

export default DatasetDetail;

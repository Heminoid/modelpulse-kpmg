import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([AllCommunityModule]);

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
import { ArrowLeft, CheckCircle, AlertTriangle, Database, BarChart2, Clock, Scale } from 'lucide-react';
import { useToast } from '../components/ui/ToastContext';
import Tabs from '../components/ui/Tabs';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import './DatasetDetail.css';

const DatasetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [dataset, setDataset] = useState(null);
  const [activeTab, setActiveTab] = useState('preview');
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
        addToast({ message: 'Mapping suggestions applied', type: 'success' });
      }
    } catch (e) {
      addToast({ message: 'Failed to get mapping suggestions', type: 'error' });
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
      addToast({ message: 'Mapping saved successfully', type: 'success' });
      
      // Validate right after saving
      const vRes = await validateMapping(id);
      setMappingValidation(vRes.data);
    } catch (e) {
      addToast({ message: 'Failed to save mapping', type: 'error' });
    }
  };

  const [quickFilterText, setQuickFilterText] = useState('');

  const getThemeClass = () => {
    return document.documentElement.getAttribute('data-theme') === 'dark' 
      ? 'ag-theme-alpine-dark' 
      : 'ag-theme-alpine';
  };

  const renderPreview = () => {
    if (loading) return <div>Loading preview...</div>;
    if (!previewData || previewData.length === 0) return <div>No preview data</div>;

    // Simplified cell renderer just for highlighting missing data
    const MissingValueRenderer = (props) => {
      if (props.value == null || props.value === '') {
        return <div className="null-cell-highlight">NULL</div>;
      }
      return <span>{props.value}</span>;
    };

    // Build dynamic column definitions with Excel-like features
    const columnDefs = Object.keys(previewData[0]).map((key, index) => {
      return {
        field: key,
        filter: 'agTextColumnFilter', // Explicitly use text filter for floating support
        floatingFilter: true, // Ensure floating filters are visible
        sortable: true,
        resizable: true,
        pinned: index === 0 ? 'left' : null, // Freeze Panes
        cellRenderer: MissingValueRenderer,
      };
    });

    return (
      <div className="preview-container">
        <div className="preview-header">
          <div>
            <h3 className="preview-title">Data Explorer</h3>
            <p className="preview-description">Excel-style smart grid with missing value highlighting and global search.</p>
          </div>
          <div className="preview-search-bar">
            <Database size={16} color="var(--brand-navy)" className="search-icon" />
            <input 
              type="text" 
              placeholder="Global Search (Ctrl+F)..." 
              value={quickFilterText}
              onChange={(e) => setQuickFilterText(e.target.value)}
              className="search-input"
            />
          </div>
        </div>
        
        <div className={`${getThemeClass()} ag-grid-wrapper`}>
          <AgGridReact
            rowData={previewData}
            columnDefs={columnDefs}
            defaultColDef={{
              flex: 1,
              minWidth: 150,
              filter: true,
              floatingFilter: true,
              resizable: true,
              sortable: true,
            }}
            quickFilterText={quickFilterText}
            rowSelection="multiple"
            enableRangeSelection={true}
          />
        </div>
      </div>
    );
  };

  const renderProfile = () => {
    if (loading) return <div>Loading profile...</div>;
    if (!profileData) return <div>No profile data</div>;

    const profileColumns = [
      { 
        key: 'name', 
        label: 'Column Name', 
        render: row => (
          <div className="column-name-cell">
            {row.name}
            {row.flags?.includes('protected_class_risk') && (
              <Badge status="critical">⚠️ Bias Risk</Badge>
            )}
          </div>
        )
      },
      { key: 'inferred_type', label: 'Inferred Type', render: row => <Badge status="info">{row.inferred_type}</Badge> },
      { key: 'null_count', label: 'Null Count', render: row => `${row.null_count} (${(row.null_percent * 100).toFixed(1)}%)` },
      { key: 'unique_count', label: 'Unique Count', render: row => row.unique_count }
    ];

    return (
      <div className="tab-content-flex">
        <Card title="Summary">
          <div className="summary-grid">
            <div>
              <p className="summary-label">Row Count</p>
              <p className="summary-value">{profileData.row_count}</p>
            </div>
            <div>
              <p className="summary-label">Column Count</p>
              <p className="summary-value">{profileData.column_count}</p>
            </div>
            <div>
              <p className="summary-label">Duplicate Rows</p>
              <p className="summary-value">{profileData.duplicate_row_count}</p>
            </div>
          </div>
        </Card>
        
        <Card title="Column Profiles">
          <DataTable 
            columns={profileColumns}
            data={profileData.columns || []}
            emptyMessage="No columns found."
          />
        </Card>
      </div>
    );
  };

  const renderMapping = () => {
    const mappingColumns = [
      { 
        key: 'name', 
        label: 'Column Name', 
        render: row => (
          <div className="column-name-cell">
            {row.name}
            {row.flags?.includes('protected_class_risk') && (
              <Badge status="critical">⚠️ Bias Risk</Badge>
            )}
          </div>
        )
      },
      { key: 'inferred_type', label: 'Inferred Type', render: row => <Badge status="info">{row.inferred_type}</Badge> },
      { 
        key: 'role', 
        label: 'Mapping Role', 
        render: row => {
          const isBiasRisk = row.flags?.includes('protected_class_risk');
          const currentVal = columnMappings[row.name] || 'feature_field';
          const hasViolation = isBiasRisk && currentVal === 'feature_field';
          
          return (
            <div>
              <select 
                className={`mapping-select ${hasViolation ? 'border-red-500' : ''}`}
                value={currentVal}
                onChange={(e) => {
                  setColumnMappings({...columnMappings, [row.name]: e.target.value});
                }}
              >
                <option value="record_id">Record ID / Primary Key</option>
                <option value="target">Target / Label</option>
                <option value="event_time">Event Date / Time</option>
                <option value="feature_field">Feature (Input)</option>
                <option value="segment_field">Categorical / Segment</option>
                <option value="protected_class">Protected Class (Fairness)</option>
                <option value="prediction_score">Prediction Score</option>
                <option value="prediction_probability">Prediction Probability</option>
                <option value="decision">Decision</option>
                <option value="dpd_field">Days Past Due (DPD)</option>
                <option value="amount_field">Amount Field</option>
                <option value="score_band">Score Band</option>
                <option value="risk_band">Risk Band</option>
                <option value="ignored">Ignore Field</option>
              </select>
              {hasViolation && (
                <div className="violation-note">
                  ECOA Violation: Cannot use as input feature
                </div>
              )}
            </div>
          )
        }
      }
    ];

    // Compute Checklist
    const mappedRoles = Object.values(columnMappings || {});
    const hasTarget = mappedRoles.includes('target');
    const hasDate = mappedRoles.includes('event_time');
    const hasProtected = mappedRoles.includes('protected_class');

    return (
      <div className="tab-content-flex">
        <Card>
          <div className="mapping-header">
            <div>
              <h3 className="mapping-title">Column Mapping</h3>
              <p className="mapping-subtitle">Map your dataset columns to logical roles for model monitoring.</p>
            </div>
            <div className="mapping-actions">
              <button className="btn btn-secondary" onClick={handleSuggestMapping}>Auto-Suggest</button>
              <button className="btn btn-primary" onClick={handleSaveMapping}>Approve & Lock Schema</button>
            </div>
          </div>

          {/* MRM Checklist */}
          <div className="mrm-checklist-grid">
            <div className={`validation-box checklist-card ${hasTarget ? 'valid' : 'invalid'}`}>
              <div className="checklist-header">
                <BarChart2 size={20} color="var(--brand-navy)"/>
                <strong className="checklist-title">Outcomes Analysis</strong>
              </div>
              <div className="checklist-desc">
                Unlocks performance tracking (Accuracy, ROC-AUC, Gini) by comparing predictions against ground truth. Essential for SR 11-7 validation.
              </div>
              <div className={`checklist-status ${hasTarget ? 'status-valid' : 'status-invalid'}`}>
                {hasTarget ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                <span>{hasTarget ? 'Target field mapped' : 'Requires Target / Label'}</span>
              </div>
            </div>

            <div className={`validation-box checklist-card ${hasDate ? 'valid' : 'invalid'}`}>
              <div className="checklist-header">
                <Clock size={20} color="var(--brand-navy)"/>
                <strong className="checklist-title">Vintage Analysis</strong>
              </div>
              <div className="checklist-desc">
                Enables time-series monitoring, population stability index (PSI) tracking over time, and cohort delinquency roll rates.
              </div>
              <div className={`checklist-status ${hasDate ? 'status-valid' : 'status-invalid'}`}>
                {hasDate ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                <span>{hasDate ? 'Date field mapped' : 'Requires Event Date / Time'}</span>
              </div>
            </div>

            <div className={`validation-box checklist-card ${hasProtected ? 'valid' : 'invalid'}`}>
              <div className="checklist-header">
                <Scale size={20} color="var(--brand-navy)"/>
                <strong className="checklist-title">Fairness Analysis</strong>
              </div>
              <div className="checklist-desc">
                Monitors disparate impact and equal opportunity metrics across demographic segments to ensure ECOA / Fair Lending compliance.
              </div>
              <div className={`checklist-status ${hasProtected ? 'status-valid' : 'status-invalid'}`}>
                {hasProtected ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                <span>{hasProtected ? 'Protected class mapped' : 'Requires Protected Class'}</span>
              </div>
            </div>
          </div>

          {mappingValidation && (
            <div className={`validation-box validation-box-margin ${mappingValidation.is_valid ? 'valid' : 'invalid'}`}>
              <div className="validation-header">
                {mappingValidation.is_valid ? <CheckCircle size={18} color="var(--success)"/> : <AlertTriangle size={18} color="var(--error)"/>}
                <strong>
                  {mappingValidation.is_valid ? 'Mapping is Valid' : 'Mapping Validation Failed'}
                </strong>
              </div>
              {mappingValidation.errors && mappingValidation.errors.length > 0 && (
                <ul className="validation-errors">
                  {mappingValidation.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
          )}

          <DataTable 
            columns={mappingColumns}
            data={profileData?.columns || []}
            emptyMessage="No columns to map."
          />
        </Card>
      </div>
    );
  };

  const tabs = [
    { id: 'preview', label: 'Preview' },
    { id: 'profile', label: 'Profile' },
    { id: 'mapping', label: 'Mapping' }
  ];

  return (
    <div className="dataset-detail-container">
      <div className="page-header detail-header-spacing">
        <div className="detail-header-flex">
          <button className="btn btn-secondary back-btn back-btn-custom" onClick={() => navigate('/datasets')}>
            <ArrowLeft size={20} />
          </button>
          
          <div className="dataset-title-group">
            <div className="dataset-icon-badge">
              <Database size={24} />
            </div>
            <div>
              <h1 className="page-title dataset-page-title">{dataset?.filename || 'Loading Dataset...'}</h1>
              <p className="page-subtitle dataset-id-subtitle">ID: {id}</p>
            </div>
          </div>
        </div>
      </div>

      <Tabs 
        tabs={tabs} 
        activeTab={activeTab} 
        onChange={setActiveTab} 
      />

      <div className="dataset-tab-panel">
        {activeTab === 'preview' && renderPreview()}
        {activeTab === 'profile' && renderProfile()}
        {activeTab === 'mapping' && renderMapping()}
      </div>
    </div>
  );
};

export default DatasetDetail;

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import { getDatasets, uploadDataset, deleteDataset } from '../services/api';
import { Upload, Trash2, FileSpreadsheet, Eye, Plus } from 'lucide-react';

const Datasets = () => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const res = await getDatasets();
      setDatasets(res.data || []);
    } catch (error) {
      console.error("Failed to load datasets:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await uploadDataset(file);
      await fetchDatasets();
    } catch (error) {
      console.error("Upload failed", error);
      alert("Failed to upload dataset.");
    } finally {
      setUploading(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (datasetId) => {
    if (!window.confirm("Are you sure you want to delete this dataset?")) return;
    
    try {
      await deleteDataset(datasetId);
      setDatasets(datasets.filter(d => d.id !== datasetId));
    } catch (error) {
      console.error("Delete failed", error);
      alert("Failed to delete dataset.");
    }
  };

  return (
    <div className="datasets-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">Datasets</h1>
          <p className="page-subtitle">Manage your training and inference data.</p>
        </div>
        
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".csv,.json"
          onChange={handleFileChange} 
        />
        
        <button 
          className="btn btn-primary" 
          onClick={handleUploadClick}
          disabled={uploading}
        >
          {uploading ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTop: '2px solid white', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
              Uploading...
            </span>
          ) : (
            <><Upload size={18} /> Upload Dataset</>
          )}
        </button>
      </div>

      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>

      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            Loading datasets...
          </div>
        ) : datasets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <FileSpreadsheet size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No datasets found</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Upload your first dataset to start monitoring.</p>
            <button className="btn btn-primary" onClick={handleUploadClick}><Plus size={18} /> Add Dataset</button>
          </div>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Rows</th>
                  <th>Columns</th>
                  <th>Size</th>
                  <th>Uploaded</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset) => (
                  <tr key={dataset.id}>
                    <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <FileSpreadsheet size={16} color="var(--accent-primary)" />
                        {dataset.filename || dataset.name}
                      </div>
                    </td>
                    <td>{dataset.row_count?.toLocaleString() || '-'}</td>
                    <td>{dataset.column_count || '-'}</td>
                    <td>{dataset.file_size_bytes ? (dataset.file_size_bytes / 1024).toFixed(2) + ' KB' : '-'}</td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {new Date(dataset.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)' }} 
                          onClick={() => navigate(`/datasets/${dataset.id}`)}
                          title="View Profile"
                        >
                          <Eye size={16} />
                        </button>
                        <button 
                          className="btn btn-danger" 
                          style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}
                          onClick={() => handleDelete(dataset.id)}
                          title="Delete Dataset"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
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

export default Datasets;

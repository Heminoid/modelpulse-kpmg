import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import { getDatasets, uploadDataset, deleteDataset } from '../services/api';
import { Upload, Trash2, FileSpreadsheet, Eye, Plus } from 'lucide-react';
import { useToast } from '../components/ui/ToastContext';
import Modal from '../components/ui/Modal';
import DataTable from '../components/ui/DataTable';
import './Datasets.css';

const Datasets = () => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [datasetToDelete, setDatasetToDelete] = useState(null);
  
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const { addToast } = useToast();

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
      addToast({ message: 'Dataset uploaded successfully', type: 'success' });
    } catch (error) {
      console.error("Upload failed", error);
      addToast({ message: 'Failed to upload dataset', type: 'error' });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const confirmDelete = async () => {
    if (!datasetToDelete) return;
    try {
      await deleteDataset(datasetToDelete);
      setDatasets(datasets.filter(d => d.id !== datasetToDelete));
      addToast({ message: 'Dataset deleted successfully', type: 'success' });
    } catch (error) {
      console.error("Delete failed", error);
      addToast({ message: 'Failed to delete dataset', type: 'error' });
    } finally {
      setDatasetToDelete(null);
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Name',
      render: (row) => (
        <div className="dataset-name-cell">
          <FileSpreadsheet size={16} className="text-accent" />
          <span className="font-medium text-primary">{row.filename || row.name}</span>
        </div>
      )
    },
    {
      key: 'rows',
      label: 'Rows',
      render: (row) => row.row_count?.toLocaleString() || '-'
    },
    {
      key: 'columns',
      label: 'Columns',
      render: (row) => row.column_count || '-'
    },
    {
      key: 'size',
      label: 'Size',
      render: (row) => row.file_size_bytes ? (row.file_size_bytes / 1024).toFixed(2) + ' KB' : '-'
    },
    {
      key: 'uploaded',
      label: 'Uploaded',
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
        <div className="actions-cell">
          <button 
            className="btn btn-secondary action-btn" 
            onClick={() => navigate(`/datasets/${row.id}`)}
            title="View Profile"
          >
            <Eye size={16} />
          </button>
          <button 
            className="btn btn-danger action-btn" 
            onClick={() => setDatasetToDelete(row.id)}
            title="Delete Dataset"
          >
            <Trash2 size={16} />
          </button>
        </div>
      )
    }
  ];

  return (
    <div className="datasets-container">
      <div className="page-header header-spacing">
        <div>
          <h1 className="page-title">Datasets</h1>
          <p className="page-subtitle">Manage your training and inference data.</p>
        </div>
        
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden-input"
          accept=".csv,.json"
          onChange={handleFileChange} 
        />
        
        <button 
          className="btn btn-primary" 
          onClick={handleUploadClick}
          disabled={uploading}
        >
          {uploading ? (
            <span className="uploading-indicator">
              <div className="spinner-small"></div>
              Uploading...
            </span>
          ) : (
            <><Upload size={18} /> Upload Dataset</>
          )}
        </button>
      </div>

      <Card>
        {loading ? (
          <div className="loading-state">
            Loading datasets...
          </div>
        ) : datasets.length === 0 ? (
          <div className="empty-state">
            <FileSpreadsheet size={48} className="empty-icon" />
            <h3 className="empty-title">No datasets found</h3>
            <p className="empty-subtitle">Upload your first dataset to start monitoring.</p>
            <button className="btn btn-primary" onClick={handleUploadClick}>
              <Plus size={18} /> Add Dataset
            </button>
          </div>
        ) : (
          <DataTable 
            columns={columns}
            data={datasets}
            emptyMessage="No datasets available."
          />
        )}
      </Card>

      <Modal 
        isOpen={!!datasetToDelete} 
        onClose={() => setDatasetToDelete(null)}
        onConfirm={confirmDelete}
        title="Delete Dataset"
        variant="danger"
        confirmText="Delete"
        cancelText="Cancel"
      >
        <p>Are you sure you want to delete this dataset? This action cannot be undone.</p>
      </Modal>
    </div>
  );
};

export default Datasets;

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error.response?.data || error.message);
  }
);

// --- Datasets ---
export const getDatasets = (page = 1, limit = 20) => apiClient.get(`/datasets?page=${page}&limit=${limit}`);
export const getDataset = (datasetId) => apiClient.get(`/datasets/${datasetId}`);
export const getDatasetProfile = (datasetId) => apiClient.get(`/datasets/${datasetId}/profile`);
export const getDatasetPreview = (datasetId, rows = 50) => apiClient.get(`/datasets/${datasetId}/preview?rows=${rows}`);
export const deleteDataset = (datasetId) => apiClient.delete(`/datasets/${datasetId}`);
export const uploadDataset = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// --- Mappings ---
export const suggestMapping = (datasetId) => apiClient.post(`/datasets/${datasetId}/suggest-mapping`);
export const saveMapping = (datasetId, payload) => apiClient.post(`/datasets/${datasetId}/save-mapping`, payload);
export const getMapping = (datasetId) => apiClient.get(`/datasets/${datasetId}/mapping`);
export const validateMapping = (datasetId) => apiClient.get(`/datasets/${datasetId}/mapping/validate`);

// --- Monitors ---
export const createMonitor = (payload) => apiClient.post('/monitors', payload);
export const getMonitors = (page = 1, limit = 20) => apiClient.get(`/monitors?page=${page}&limit=${limit}`);
export const getMonitor = (monitorId) => apiClient.get(`/monitors/${monitorId}`);
export const triggerRun = (monitorId) => apiClient.post(`/monitors/${monitorId}/run`);

// --- Registry ---
export const createModel = (payload) => apiClient.post('/registry/models', payload);
export const getModels = (page = 1, limit = 20, stage = null) => {
  let url = `/registry/models?page=${page}&limit=${limit}`;
  if (stage) url += `&stage=${stage}`;
  return apiClient.get(url);
};
export const getChampion = () => apiClient.get('/registry/champion');
export const getModel = (modelId) => apiClient.get(`/registry/models/${modelId}`);
export const updateModel = (modelId, payload) => apiClient.put(`/registry/models/${modelId}`, payload);
export const linkRun = (modelId, runId) => apiClient.post(`/registry/models/${modelId}/link-run/${runId}`);
export const getChampionChallenger = (championId, challengerId) => 
  apiClient.get(`/registry/champion-challenger?champion_id=${championId}&challenger_id=${challengerId}`);

// --- Reports ---
export const generateReport = (runId, payload) => apiClient.post(`/runs/${runId}/reports/generate`, payload);
export const getReports = (runId) => apiClient.get(`/runs/${runId}/reports`);
// Download doesn't go through axios easily if we want file saving, but we can export the URL generator
export const getReportDownloadUrl = (runId, reportId) => `${API_BASE_URL}/runs/${runId}/reports/${reportId}/download`;

// --- Runs ---
export const getRuns = (monitorId = null, page = 1, limit = 20) => {
  let url = `/runs?page=${page}&limit=${limit}`;
  if (monitorId) url += `&monitor_id=${monitorId}`;
  return apiClient.get(url);
};
export const getRun = (runId) => apiClient.get(`/runs/${runId}`);
export const deleteRun = (runId) => apiClient.delete(`/runs/${runId}`);
export const getRunMetrics = (runId) => apiClient.get(`/runs/${runId}/metrics`);
export const getRunCharts = (runId) => apiClient.get(`/runs/${runId}/charts`);
export const getChartImageUrl = (runId, chartId, format = 'png') => `${API_BASE_URL}/runs/${runId}/charts/${chartId}/image?format=${format}`;
export const getRunStatTests = (runId) => apiClient.get(`/runs/${runId}/stat-tests`);
export const getRunVintage = (runId) => apiClient.get(`/runs/${runId}/vintage`);
export const getRunOverrideAnalysis = (runId, scoreCutoff = 600) => apiClient.get(`/runs/${runId}/override-analysis?score_cutoff=${scoreCutoff}`);
export const getRunFairness = (runId) => apiClient.get(`/runs/${runId}/fairness`);
export const getRunTimeSeries = (runId) => apiClient.get(`/runs/${runId}/time-series`);
export const generateNarrative = (runId) => apiClient.post(`/runs/${runId}/narratives`);
export const getNarratives = (runId) => apiClient.get(`/runs/${runId}/narratives`);

// --- Health ---
export const getHealth = () => apiClient.get('/health');

export default apiClient;

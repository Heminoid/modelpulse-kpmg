import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getRuns, getReports, generateReport, getReportDownloadUrl, getMonitors, getReportQA } from '../services/api';
import { FileText, Download, FileUp } from 'lucide-react';
import { useToast } from '../components/ui/ToastContext';
import DataTable from '../components/ui/DataTable';
import Badge from '../components/ui/Badge';
import './Reports.css';

const AVAILABLE_SECTIONS = [
  { id: 'narrative', name: 'AI Narrative / Executive Summary', default: true },
  { id: 'alerts', name: 'Alerts & Breaches', default: true },
  { id: 'performance', name: 'Performance Analysis', default: true },
  { id: 'calibration', name: 'Calibration Assessment', default: true },
  { id: 'stability', name: 'Stability / Drift', default: true },
  { id: 'data_quality', name: 'Data Quality', default: true },
  { id: 'fairness', name: 'Discrimination Testing', default: true },
  { id: 'delinquency', name: 'Delinquency Analysis', default: true },
  { id: 'insights', name: 'Key Insights (Findings)', default: true },
  { id: 'segments', name: 'Segment Breakdown', default: true },
  { id: 'timeseries', name: 'Time-Series Cohort Trends', default: true },
  { id: 'stat_tests', name: 'Statistical Tests', default: true },
  { id: 'charts', name: 'Charts & Visualizations', default: true },
  { id: 'vintage', name: 'Vintage Analysis', default: false },
  { id: 'override', name: 'Override Analysis', default: false },
];

const Reports = () => {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const { addToast } = useToast();

  // Form State
  const [reportType, setReportType] = useState('full_technical');
  const [reportFormat, setReportFormat] = useState('html');
  const [selectedSections, setSelectedSections] = useState(
    AVAILABLE_SECTIONS.filter(s => s.default).map(s => s.id)
  );
  const [reportQA, setReportQA] = useState({});

  const [monitors, setMonitors] = useState([]);

  useEffect(() => {
    const fetchBase = async () => {
      try {
        const [runsRes, monitorsRes] = await Promise.all([
          getRuns(),
          getMonitors()
        ]);
        setRuns(runsRes.data || []);
        setMonitors(monitorsRes.data || []);
        if (runsRes.data && runsRes.data.length > 0) {
          setSelectedRunId(runsRes.data[0].run_id);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchBase();
  }, []);

  useEffect(() => {
    if (selectedRunId) {
      fetchReports(selectedRunId);
    }
  }, [selectedRunId]);

  const fetchReports = async (runId) => {
    setLoading(true);
    try {
      const res = await getReports(runId);
      const fetchedReports = res.data || [];
      setReports(fetchedReports);

      // Fetch QA scores for each report
      const qaScores = {};
      await Promise.all(fetchedReports.map(async (r) => {
        try {
          const qaRes = await getReportQA(runId, r.report_type);
          qaScores[r.report_id] = qaRes.data?.score;
        } catch(e) {
          qaScores[r.report_id] = null;
        }
      }));
      setReportQA(qaScores);
    } catch (e) {
      console.error(e);
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!selectedRunId) return;

    setGenerating(true);
    try {
      await generateReport(selectedRunId, { report_type: reportType, format: reportFormat, sections: selectedSections });
      await fetchReports(selectedRunId);
      addToast({ message: 'Report generated successfully', type: 'success' });
    } catch (e) {
      addToast({ message: 'Failed to generate report. Check backend logs for details.', type: 'error' });
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (reportId) => {
    const link = document.createElement('a');
    link.href = getReportDownloadUrl(selectedRunId, reportId);
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const columns = [
    { 
      key: 'type', 
      label: 'Type', 
      render: row => (
        <span className="capitalize-text">
          {(row.report_type || '').replace('_', ' ')}
        </span>
      )
    },
    { 
      key: 'format', 
      label: 'Format', 
      render: row => (
        <Badge status={row.format === 'pdf' ? 'error' : 'info'} size="small">
          <span className="uppercase-text">{row.format}</span>
        </Badge>
      )
    },
    { 
      key: 'generated_at', 
      label: 'Generated At', 
      render: row => (
        <span className="text-muted">
          {row.generated_at ? new Date(row.generated_at).toLocaleString() : 'Unknown'}
        </span>
      )
    },
    {
      key: 'qa',
      label: 'QA Status',
      render: row => {
        const score = reportQA[row.report_id];
        if (score === undefined || score === null) return <span className="text-muted">N/A</span>;
        if (score >= 100) return <Badge status="healthy">QA: Complete</Badge>;
        if (score >= 70) return <Badge status="warning">QA: {score}%</Badge>;
        return <Badge status="critical">QA: {score}%</Badge>;
      }
    },
    { 
      key: 'actions', 
      label: 'Actions', 
      align: 'right',
      render: row => (
        <button className="btn btn-secondary download-btn" onClick={() => handleDownload(row.report_id)}>
          <Download size={16} /> Download
        </button>
      )
    }
  ];

  return (
    <div className="reports-container">
      <div className="page-header header-spacing">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Generate and download executive reports.</p>
        </div>
      </div>

      <div className="reports-grid">
        <Card title="Generate Report" icon={FileUp}>
          <form onSubmit={handleGenerate} className="form-layout">
            <div className="form-group">
              <label className="form-label" htmlFor="report-run">Select Run</label>
              <select
                id="report-run"
                value={selectedRunId}
                onChange={e => setSelectedRunId(e.target.value)}
                className="form-input"
              >
                {runs.map(r => {
                  const mon = monitors.find(m => m.monitor_id === r.monitor_id);
                  const monitorName = mon ? mon.name : 'Unknown Monitor';
                  return (
                    <option key={r.run_id} value={r.run_id}>
                      {monitorName} - {r.run_id.substring(0, 8)} ({r.started_at ? new Date(r.started_at).toLocaleDateString() : 'Unknown'})
                    </option>
                  );
                })}
              </select>
            </div>
            
            <div className="form-group">
              <label className="form-label" htmlFor="report-type">Report Type</label>
              <select
                id="report-type"
                value={reportType}
                onChange={e => setReportType(e.target.value)}
                className="form-input"
              >
                <option value="full_technical">Full Technical Report</option>
                <option value="executive_summary">Executive Summary</option>
                <option value="data_quality">Data Quality Report</option>
                <option value="sr_11_7">SR 11-7 Checklist</option>
                <option value="ifrs9">IFRS9 Monitoring</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="report-format">Format</label>
              <select
                id="report-format"
                value={reportFormat}
                onChange={e => setReportFormat(e.target.value)}
                className="form-input"
              >
                <option value="html">HTML</option>
                <option value="pdf">PDF</option>
                <option value="docx">DOCX</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Include Sections</label>
              <div className="sections-checkboxes" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {AVAILABLE_SECTIONS.map(section => (
                  <label key={section.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input 
                      type="checkbox"
                      checked={selectedSections.includes(section.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedSections([...selectedSections, section.id]);
                        } else {
                          setSelectedSections(selectedSections.filter(id => id !== section.id));
                        }
                      }}
                    />
                    {section.name}
                  </label>
                ))}
              </div>
            </div>

            <button type="submit" className="btn btn-primary submit-btn" disabled={generating || !selectedRunId}>
              {generating ? 'Generating...' : 'Generate Report'}
            </button>
          </form>
        </Card>

        <Card title="Available Reports" icon={FileText}>
          {loading ? (
            <div>Loading...</div>
          ) : reports.length === 0 ? (
            <div className="empty-state">
              No reports found for this run. Generate one on the left.
            </div>
          ) : (
            <DataTable columns={columns} data={reports} />
          )}
        </Card>
      </div>
    </div>
  );
};

export default Reports;

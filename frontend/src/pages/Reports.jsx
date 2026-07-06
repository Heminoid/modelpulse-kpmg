import React, { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getRuns, getReports, generateReport, getReportDownloadUrl, getMonitors } from '../services/api';
import { FileText, Download, FileUp } from 'lucide-react';

const Reports = () => {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Form State
  const [reportType, setReportType] = useState('full_technical');
  const [reportFormat, setReportFormat] = useState('html');

  const [monitors, setMonitors] = useState([]);

  useEffect(() => {
    const fetchBase = async () => {
      try {
        const [runsRes, monitorsRes] = await Promise.all([
          getRuns(),
          getMonitors() // Assumes getMonitors is exported from api.js
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
      setReports(res.data || []);
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
      await generateReport(selectedRunId, { report_type: reportType, format: reportFormat });
      await fetchReports(selectedRunId);
    } catch (e) {
      alert("Failed to generate report. Check backend logs for details.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (reportId) => {
    // Instead of axios, we use standard browser navigation to trigger a download
    window.location.href = getReportDownloadUrl(selectedRunId, reportId);
  };

  return (
    <div className="reports-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Generate and download executive reports.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        <Card title="Generate Report" icon={FileUp}>
          <form onSubmit={handleGenerate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Select Run</label>
              <select 
                value={selectedRunId}
                onChange={e => setSelectedRunId(e.target.value)}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
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
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Report Type</label>
              <select 
                value={reportType}
                onChange={e => setReportType(e.target.value)}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
              >
                <option value="full_technical">Full Technical Report</option>
                <option value="executive_summary">Executive Summary</option>
                <option value="data_quality">Data Quality Report</option>
                <option value="sr_11_7">SR 11-7 Checklist</option>
                <option value="ifrs9">IFRS9 Monitoring</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ color: 'var(--text-secondary)' }}>Format</label>
              <select 
                value={reportFormat}
                onChange={e => setReportFormat(e.target.value)}
                style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
              >
                <option value="html">HTML</option>
                <option value="pdf">PDF</option>
              </select>
            </div>

            <button type="submit" className="btn btn-primary" disabled={generating || !selectedRunId} style={{ marginTop: '1rem' }}>
              {generating ? 'Generating...' : 'Generate Report'}
            </button>
          </form>
        </Card>

        <Card title="Available Reports" icon={FileText}>
          {loading ? (
            <div>Loading...</div>
          ) : reports.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              No reports found for this run. Generate one on the left.
            </div>
          ) : (
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Format</th>
                    <th>Generated At</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <tr key={report.report_id}>
                      <td style={{ textTransform: 'capitalize' }}>{(report.report_type || '').replace('_', ' ')}</td>
                      <td>
                        <span style={{ 
                          background: report.format === 'pdf' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(99, 102, 241, 0.2)',
                          color: report.format === 'pdf' ? 'var(--error)' : 'var(--accent-secondary)',
                          padding: '0.25rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.8rem',
                          fontWeight: 'bold',
                          textTransform: 'uppercase'
                        }}>
                          {report.format}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{report.generated_at ? new Date(report.generated_at).toLocaleString() : 'Unknown'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button className="btn btn-secondary" style={{ padding: '0.5rem' }} onClick={() => handleDownload(report.report_id)}>
                          <Download size={16} /> Download
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
    </div>
  );
};

export default Reports;

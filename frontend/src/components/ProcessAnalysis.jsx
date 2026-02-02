/**
 * ProcessAnalysis – Displays FD analysis for a selected process.
 * Backend: GET /process/{pid}/analysis →
 *   { table, type_counts, non_standard, severity, severity_reason, severity_condition,
 *     analysis, usage_pct, fd_density, fd_danger_rank, fd_danger_reason }
 */

import React, { useState } from 'react';
import { fetchProcessAnalysisPdf } from '../api/fdForensicsApi';
import FDTypePieChart from './FDTypePieChart';

function severityClass(s) {
  const c = (s || '').toUpperCase();
  if (c === 'CRITICAL') return 'severity-critical';
  if (c === 'HIGH') return 'severity-high';
  if (c === 'MEDIUM') return 'severity-medium';
  return 'severity-low';
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ProcessAnalysis({ data, loading, error, pid }) {
  if (loading) {
    return (
      <div className="process-analysis loading">
        <div className="spinner" aria-hidden="true" />
        <p>Loading analysis…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="process-analysis error">
        <p className="error-msg">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="process-analysis empty">
        <p>Select a process to view FD analysis.</p>
      </div>
    );
  }

  const typeCounts = data.type_counts || {};
  const labels = Object.keys(typeCounts);
  const total = data.table?.length ?? 0;
  const [pdfLoading, setPdfLoading] = useState(false);

  async function handleDownloadPdf() {
    if (!pid) return;
    setPdfLoading(true);
    try {
      const blob = await fetchProcessAnalysisPdf(pid);
      triggerBlobDownload(blob, `fd-forensics-process-${pid}.pdf`);
    } catch {
      // Silent fail; user can retry
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <div className="process-analysis">
      <div className="analysis-actions">
        <button
          type="button"
          className="btn-download-pdf"
          onClick={handleDownloadPdf}
          disabled={pdfLoading}
        >
          {pdfLoading ? 'Generating…' : 'Download PDF'}
        </button>
      </div>
      {data.snapshot_taken_at && (
        <p className="snapshot-time">
          <strong>Snapshot taken (UTC):</strong> <span className="mono">{data.snapshot_taken_at}</span>
        </p>
      )}
      <section className="metrics">
        <h3>Metrics</h3>
        <div className="metric-grid">
          <div className="metric">
            <span className="metric-label">Total FDs</span>
            <span className="metric-value">{total}</span>
            <span className="metric-def">Open file descriptors (handles to files, sockets, pipes).</span>
          </div>
          <div className="metric">
            <span className="metric-label">Non-Standard</span>
            <span className="metric-value">{data.non_standard}</span>
            <span className="metric-def">FDs other than stdin (0), stdout (1), stderr (2).</span>
          </div>
          <div className="metric">
            <span className="metric-label">FD Density</span>
            <span className="metric-value mono">
              {typeof data.fd_density === 'number' ? data.fd_density.toFixed(2) : '—'}
            </span>
            <span className="metric-def">Ratio of non-standard FDs to total; higher = more kernel-managed resources.</span>
          </div>
          {data.usage_pct != null && (
            <div className="metric">
              <span className="metric-label">Usage vs Limit</span>
              <span className="metric-value">{data.usage_pct.toFixed(1)}%</span>
              <span className="metric-def">How much of the max FDs this process is allowed to have open is currently in use.</span>
            </div>
          )}
          <div className={`metric severity-badge ${severityClass(data.severity)}`}>
            <span className="metric-label">Severity</span>
            <span className="metric-value">{data.severity}</span>
            <span className="metric-def">Risk level from FD count and limit usage.</span>
          </div>
        </div>
        <p className="severity-note">
          {data.severity_reason} ({data.severity_condition})
        </p>
      </section>

      {data.analysis?.length > 0 && (
        <section className="interpretation">
          <h3>Forensic Interpretation</h3>
          <ul>
            {data.analysis.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </section>
      )}

      {labels.length > 0 && (
        <section className="type-breakdown">
          <h3>FD Type Breakdown</h3>
          <div className="fd-type-chart-wrap">
            <FDTypePieChart typeCounts={typeCounts} />
          </div>
          <div className="type-list">
            {labels.map((t) => (
              <div key={t} className="type-row">
                <span className="type-name">{t}</span>
                <span className="mono">{typeCounts[t]}</span>
                {data.fd_danger_reason?.[t] && (
                  <span className="type-reason">{data.fd_danger_reason[t]}</span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {data.table?.length > 0 && (
        <section className="fd-table-section">
          <h3>File Descriptor Table</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>FD</th>
                  <th>Target</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {data.table.map((row, i) => (
                  <tr key={i}>
                    <td className="mono">{row.FD}</td>
                    <td className="mono target">{row.Target}</td>
                    <td>{row.Type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default ProcessAnalysis;

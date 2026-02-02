/**
 * CodeAnalysis – Upload Python file, run analysis, show results.
 * Calls POST /analyze/code, displays execution metadata, FD growth chart,
 * FD table, and AI summary. Gemini API key can be entered in the UI.
 */

import React, { useState, useEffect, useRef } from 'react';
import { analyzeCode, analyzeCodePdf, normalizeError } from '../api/fdForensicsApi';
import CodeUpload from '../components/CodeUpload';
import FDGrowthChart from '../components/FDGrowthChart';
import AISummary from '../components/AISummary';

const GEMINI_KEY_STORAGE = 'fd_forensics_gemini_api_key';

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function CodeAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [lastFile, setLastFile] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [geminiKey, setGeminiKey] = useState('');
  const [geminiKeySaved, setGeminiKeySaved] = useState(false);
  const geminiKeyInputRef = useRef(null);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(GEMINI_KEY_STORAGE);
      if (stored) {
        setGeminiKey(stored);
        setGeminiKeySaved(true);
      }
    } catch {
      // ignore
    }
  }, []);

  function handleSaveGeminiKey() {
    const trimmed = (geminiKey || '').trim();
    if (trimmed) {
      try {
        sessionStorage.setItem(GEMINI_KEY_STORAGE, trimmed);
        setGeminiKeySaved(true);
      } catch {
        // ignore
      }
    } else {
      try {
        sessionStorage.removeItem(GEMINI_KEY_STORAGE);
        setGeminiKeySaved(false);
      } catch {
        // ignore
      }
    }
  }

  function getGeminiKeyForRequest() {
    const fromInput = geminiKeyInputRef.current?.value?.trim();
    if (fromInput) return fromInput;
    const fromState = (geminiKey || '').trim();
    if (fromState) return fromState;
    try {
      const stored = sessionStorage.getItem(GEMINI_KEY_STORAGE);
      if (stored) return stored;
    } catch {
      // ignore
    }
    return '';
  }

  async function handleUpload(file) {
    setLoading(true);
    setError(null);
    setResult(null);
    setLastFile(file);
    const keyToUse = getGeminiKeyForRequest();
    try {
      const data = await analyzeCode(file, keyToUse);
      setResult(data);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadPdf() {
    if (!lastFile) return;
    setPdfLoading(true);
    const keyToUse = getGeminiKeyForRequest();
    try {
      const blob = await analyzeCodePdf(lastFile, keyToUse);
      const ts = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '').replace('T', '-');
      triggerBlobDownload(blob, `fd-forensics-code-${ts}.pdf`);
    } catch {
      // Silent fail
    } finally {
      setPdfLoading(false);
    }
  }

  const raw = result?.raw_analysis;
  const exec = raw?.execution;
  const fdAnalysis = raw?.fd_analysis;

  return (
    <div className="page code-analysis">
      <header className="page-header">
        <h1>Code Analysis</h1>
        <p>Upload a Python or C file. It will be compiled (C) or executed in a sandbox with FD tracking.</p>
      </header>

      <section className="card gemini-key-card">
        <h3>Gemini API Key (for AI Forensic Summary)</h3>
        <p className="gemini-key-hint">Paste your key below, then upload a file and run analysis. The key is only sent with your request and stored in this browser session.</p>
        <div className="gemini-key-row">
          <input
            ref={geminiKeyInputRef}
            type="password"
            className="gemini-key-input"
            placeholder="Paste your Gemini API key here"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            aria-label="Gemini API key"
          />
          <button
            type="button"
            className="btn-save-key"
            onClick={handleSaveGeminiKey}
          >
            {geminiKeySaved ? 'Saved for this session' : 'Save for this session'}
          </button>
        </div>
        <p className="gemini-key-link">
          Get a key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>.
        </p>
      </section>

      <CodeUpload onUpload={handleUpload} loading={loading} disabled={loading} />

      {error && (
        <div className="banner error">
          {error}
        </div>
      )}

      {result && (
        <div className="analysis-result">
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
          {exec && (
            <section className="card execution-meta">
              <h3>Execution Metadata</h3>
              {exec.termination_reason === 'compile_error' && (
                <div className="banner compile-error" role="alert">
                  Compilation failed. See stderr below.
                </div>
              )}
              <div className="meta-grid">
                <div className="meta-item">
                  <span className="meta-label">Language</span>
                  <span className="mono">{exec.language ?? 'python'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">PID</span>
                  <span className="mono">{exec.pid ?? '—'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Duration</span>
                  <span className="mono">{exec.duration_seconds != null ? `${exec.duration_seconds}s` : '—'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Termination</span>
                  <span className={`termination-badge ${exec.termination_reason}`}>
                    {exec.termination_reason}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Exit Code</span>
                  <span className="mono">{exec.exit_code ?? '—'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">FD Limit</span>
                  <span className="mono">{exec.fd_limit ?? '—'}</span>
                </div>
                {exec.sampling_started_at && (
                  <div className="meta-item meta-item-full">
                    <span className="meta-label">Execution snapshot at</span>
                    <span className="mono">{exec.sampling_started_at}</span>
                  </div>
                )}
                {exec.snapshot_taken_at && (
                  <div className="meta-item meta-item-full">
                    <span className="meta-label">Snapshot taken (UTC)</span>
                    <span className="mono">{exec.snapshot_taken_at}</span>
                  </div>
                )}
              </div>
              {exec.termination_reason === 'compile_error' && exec.stderr && (
                <div className="output output-compile-errors">
                  <strong>Compilation errors</strong>
                  <pre className="mono stderr output-pre">{exec.stderr}</pre>
                </div>
              )}
              {exec.stdout && (
                <div className="output">
                  <strong>stdout</strong>
                  <pre className="mono output-pre">{exec.stdout}</pre>
                </div>
              )}
              {exec.stderr && exec.termination_reason !== 'compile_error' && (
                <div className="output">
                  <strong>stderr</strong>
                  <pre className="mono stderr output-pre">{exec.stderr}</pre>
                </div>
              )}
            </section>
          )}

          <section className="card" key={`fd-growth-${exec?.pid ?? 'none'}-${(raw?.fd_growth?.length ?? 0)}-${exec?.duration_seconds ?? 0}`}>
            <h3>FD Growth Over Time</h3>
            <FDGrowthChart data={raw?.fd_growth ?? []} />
          </section>

          {fdAnalysis && (
            <section className="card fd-analysis-card">
              <h3>FD Analysis</h3>
              <div className="metrics-inline">
                <span>Total: {fdAnalysis.table?.length ?? 0}</span>
                <span>Non-standard: {fdAnalysis.non_standard}</span>
                <span>Severity: <span className={`severity-badge severity-${(fdAnalysis.severity || '').toLowerCase()}`}>{fdAnalysis.severity}</span></span>
              </div>
              {fdAnalysis.table?.length > 0 && (
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
                      {fdAnalysis.table.map((row, i) => (
                        <tr key={i}>
                          <td className="mono">{row.FD ?? row.fd}</td>
                          <td className="mono target">{(row.Target ?? row.target) || '—'}</td>
                          <td>{row.Type ?? row.type ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          <section className="card ai-summary-card">
            <AISummary text={result.ai_summary} />
          </section>
        </div>
      )}
    </div>
  );
}

export default CodeAnalysis;

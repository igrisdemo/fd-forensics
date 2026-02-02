/**
 * LiveProcesses – Process list + per-process FD analysis.
 * Fetches GET /processes, then GET /process/{pid}/analysis on selection.
 */

import React, { useEffect, useState } from 'react';
import { fetchProcesses, fetchProcessAnalysis, normalizeError } from '../api/fdForensicsApi';
import ProcessList from '../components/ProcessList';
import ProcessAnalysis from '../components/ProcessAnalysis';

function LiveProcesses() {
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPid, setSelectedPid] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchProcesses()
      .then((data) => {
        if (!cancelled) {
          setProcesses(data);
          if (data.length && !selectedPid) setSelectedPid(data[0].pid);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(normalizeError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedPid) {
      setAnalysis(null);
      return;
    }
    let cancelled = false;
    setAnalysisLoading(true);
    setAnalysisError(null);
    fetchProcessAnalysis(selectedPid)
      .then((data) => {
        if (!cancelled) setAnalysis(data);
      })
      .catch((err) => {
        if (!cancelled) setAnalysisError(normalizeError(err));
      })
      .finally(() => {
        if (!cancelled) setAnalysisLoading(false);
      });
    return () => { cancelled = true; };
  }, [selectedPid]);

  return (
    <div className="page live-processes">
      <header className="page-header">
        <h1>Live Process Analysis</h1>
        <p>Select a process to view FD forensics. Snapshot at page load.</p>
      </header>

      {error && (
        <div className="banner error" role="alert">
          {error}
        </div>
      )}

      <div className="two-col">
        <aside className="sidebar">
          <h2>Processes (by FD count)</h2>
          <ProcessList
            processes={processes}
            selectedPid={selectedPid}
            onSelectPid={setSelectedPid}
            loading={loading}
            error={error}
          />
        </aside>
        <main className="content">
          <h2>FD Analysis</h2>
          <ProcessAnalysis
            data={analysis}
            loading={analysisLoading}
            error={analysisError}
            pid={selectedPid}
          />
        </main>
      </div>
    </div>
  );
}

export default LiveProcesses;

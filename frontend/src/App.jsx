import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import LiveProcesses from './pages/LiveProcesses';
import CodeAnalysis from './pages/CodeAnalysis';
import './App.css';

function formatSnapshotTime(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  const s = String(date.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${d} ${h}:${min}:${s}`;
}

function App() {
  const [snapshotTime, setSnapshotTime] = useState(null);
  useEffect(() => {
    setSnapshotTime(formatSnapshotTime(new Date()));
  }, []);

  return (
    <div className="app">
      <nav className="nav">
        <NavLink to="/" className="nav-brand">
          <span className="brand-icon">◉</span>
          File Descriptor Forensics and Code Sandbox
        </NavLink>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            Live Processes
          </NavLink>
          <NavLink to="/code" className={({ isActive }) => isActive ? 'active' : ''}>
            Code Analysis
          </NavLink>
        </div>
      </nav>
      {snapshotTime && (
        <div className="snapshot-captured-bar">
          <strong>Snapshot captured at:</strong> {snapshotTime}
        </div>
      )}

      <main className="main">
        <Routes>
          <Route path="/" element={<LiveProcesses />} />
          <Route path="/code" element={<CodeAnalysis />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

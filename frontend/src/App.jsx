import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import LiveProcesses from './pages/LiveProcesses';
import CodeAnalysis from './pages/CodeAnalysis';
import './App.css';

function App() {
  return (
    <div className="app">
      <nav className="nav">
        <NavLink to="/" className="nav-brand">
          <span className="brand-icon">◉</span>
          FD Forensics
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

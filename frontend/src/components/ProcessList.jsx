/**
 * ProcessList – Renders process list with FD counts.
 * Backend: GET /processes → Array<{ pid, name, user, fd_count }>
 */

import React from 'react';

function ProcessList({ processes, selectedPid, onSelectPid, loading, error }) {
  if (loading) {
    return (
      <div className="process-list loading">
        <div className="spinner" aria-hidden="true" />
        <p>Loading processes…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="process-list empty error">
        <p>Could not load processes.</p>
        <p className="hint">Ensure the backend is running on port 8000.</p>
      </div>
    );
  }

  if (!processes?.length) {
    return (
      <div className="process-list empty">
        <p>No processes found.</p>
      </div>
    );
  }

  return (
    <div className="process-list">
      <table>
        <thead>
          <tr>
            <th>PID</th>
            <th>Name</th>
            <th>User</th>
            <th>FD Count</th>
          </tr>
        </thead>
        <tbody>
          {processes.map((p) => (
            <tr
              key={p.pid}
              className={selectedPid === p.pid ? 'selected' : ''}
              onClick={() => onSelectPid(p.pid)}
            >
              <td className="mono">{p.pid}</td>
              <td>{p.name}</td>
              <td>{p.user}</td>
              <td className="mono fd-count">{p.fd_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ProcessList;

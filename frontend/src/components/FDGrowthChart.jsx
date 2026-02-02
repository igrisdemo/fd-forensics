/**
 * FDGrowthChart – Line chart of FD count over time.
 * Backend: raw_analysis.fd_growth → Array<{ time_sec, fd_count }>
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function FDGrowthChart({ data }) {
  if (!data?.length) {
    return (
      <div className="fd-growth-chart empty">
        <p>No FD growth data available.</p>
      </div>
    );
  }

  return (
    <div className="fd-growth-chart">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="time_sec"
            name="Time (s)"
            stroke="var(--text-muted)"
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          />
          <YAxis
            dataKey="fd_count"
            name="FD Count"
            stroke="var(--text-muted)"
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 6,
            }}
            labelStyle={{ color: 'var(--text-primary)' }}
            formatter={(value) => [value, 'FDs']}
          />
          <Line
            type="monotone"
            dataKey="fd_count"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={{ fill: 'var(--accent)', strokeWidth: 0 }}
            activeDot={{ r: 4, fill: 'var(--accent)' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default FDGrowthChart;

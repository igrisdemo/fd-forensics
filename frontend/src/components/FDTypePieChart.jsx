/**
 * FDTypePieChart – Donut chart for FD Type Breakdown.
 * Shows distribution by type with percentages and legend.
 */

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const TYPE_COLORS = {
  Standard: '#94a3b8',
  File: '#fb923c',
  Pipe: '#f97316',
  Other: '#ea580c',
  Socket: '#dc2626',
};

const TYPE_ORDER = ['Standard', 'File', 'Pipe', 'Other', 'Socket'];

function FDTypePieChart({ typeCounts }) {
  const total = Object.values(typeCounts || {}).reduce((a, b) => a + b, 0);
  if (!total || !typeCounts) {
    return null;
  }

  const keys = Object.keys(typeCounts).sort((a, b) => {
    const ai = TYPE_ORDER.indexOf(a);
    const bi = TYPE_ORDER.indexOf(b);
    if (ai >= 0 && bi >= 0) return ai - bi;
    if (ai >= 0) return -1;
    if (bi >= 0) return 1;
    return typeCounts[b] - typeCounts[a];
  });
  const data = keys.map((name) => ({
    name,
    value: typeCounts[name],
    percentage: ((typeCounts[name] / total) * 100).toFixed(1),
  }));

  if (!data.length) return null;

  return (
    <div className="fd-type-pie-chart">
      <h4 className="chart-title">FD Type Distribution by Leak Risk</h4>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="85%"
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
            label={({ name, percentage }) => `${name} ${percentage}%`}
            labelLine={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}
          >
            {data.map((entry, i) => (
              <Cell
                key={entry.name}
                fill={TYPE_COLORS[entry.name] || '#64748b'}
                stroke="var(--bg-card)"
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 8,
            }}
            formatter={(value, name, props) => [
              `${value} (${props.payload.percentage}%)`,
              name,
            ]}
          />
          <Legend
            layout="horizontal"
            align="center"
            verticalAlign="bottom"
            formatter={(value) => {
              const d = data.find((x) => x.name === value);
              return d ? `${value}: ${d.value} (${d.percentage}%)` : value;
            }}
            wrapperStyle={{ paddingTop: 12 }}
            iconType="circle"
            iconSize={10}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default FDTypePieChart;

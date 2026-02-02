/**
 * AISummary – Renders Gemini AI summary (markdown-like).
 * Backend: raw_analysis + ai_summary (string, may be fallback when Gemini unavailable)
 */

import React from 'react';

function AISummary({ text }) {
  if (!text) {
    return (
      <div className="ai-summary empty">
        <p>No AI summary available.</p>
      </div>
    );
  }

  const lines = text.split('\n');
  const blocks = [];
  let current = { type: 'p', content: [] };

  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (current.content.length) blocks.push(current);
      current = { type: 'h2', content: [line.slice(3)] };
      blocks.push(current);
      current = { type: 'p', content: [] };
    } else if (line.trim()) {
      current.content.push(line);
    } else if (current.content.length) {
      blocks.push(current);
      current = { type: 'p', content: [] };
    }
  }
  if (current.content.length) blocks.push(current);

  return (
    <div className="ai-summary">
      <h3>AI Summary</h3>
      <div className="ai-content">
        {blocks.map((block, i) => (
          <div key={i} className={`ai-block ${block.type}`}>
            {block.type === 'h2' ? (
              <h4>{block.content[0]}</h4>
            ) : (
              <p>{block.content.join(' ')}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default AISummary;

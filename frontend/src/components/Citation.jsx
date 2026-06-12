import React from 'react';

export default function Citation({ source, index }) {
  return (
    <div className="citation-card" style={{
      padding: '12px 14px',
      marginBottom: '8px',
      background: 'var(--bg-tertiary)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '6px',
      }}>
        <span className="badge badge-accent">Source {index + 1}</span>
        {source.page && (
          <span className="badge">Page {source.page}</span>
        )}
        <span className="badge">Score: {source.score}</span>
      </div>
      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: 1.6,
        margin: 0,
      }}>
        {source.text}
      </p>
    </div>
  );
}
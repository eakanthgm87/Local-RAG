import React from 'react';
import './Sidebar.css';

export default function Sidebar({
  sessions,
  currentSession,
  documents,
  selectedDoc,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  onSelectDocument,
  onDeleteDocument,
  onProcessDocument,
  onUploadClick,
  onModelSelectorClick,
  onRefreshStatus,
  ollamaStatus,
  vectorStats,
  llmProvider,
  llmModel,
  groqConfigured,
}) {
  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const getFileIcon = (type) => {
    const icons = { pdf: '📕', docx: '📘', txt: '📄' };
    return icons[type] || '📄';
  };

  const getFileTypeClass = (type) => {
    return type || 'txt';
  };

  return (
    <aside className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10h-10V2z"/>
              <path d="M12 12 20 12"/>
              <path d="M12 16 16 16"/>
            </svg>
          </div>
          <span className="sidebar-title">DocQA</span>
        </div>
        <div className="sidebar-actions">
          <button className="sidebar-btn sidebar-btn-primary" onClick={onUploadClick}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload
          </button>
          <button className="sidebar-btn" onClick={onNewSession}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Chat
          </button>
          <button className="sidebar-btn" onClick={onModelSelectorClick}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="sidebar-content">
        {/* Chat Sessions */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span>Chat History</span>
            <span className="sidebar-section-count">{sessions.length}</span>
          </div>
          {sessions.length === 0 ? (
            <div className="empty-state">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>No conversations yet. Start a new chat!</span>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`session-item ${currentSession?.id === session.id ? 'active' : ''}`}
                onClick={() => onSelectSession(session)}
              >
                <div className="session-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </div>
                <div className="session-info">
                  <div className="session-name">{session.title}</div>
                  <div className="session-date">{formatDate(session.created_at)}</div>
                </div>
                <button
                  className="session-delete-btn"
                  onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                  title="Delete session"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-divider" />

        {/* Documents */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span>Documents</span>
            <span className="sidebar-section-count">{documents.length}</span>
          </div>
          {documents.length === 0 ? (
            <div className="empty-state">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span>No documents uploaded yet.</span>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                className={`doc-item ${selectedDoc?.id === doc.id ? 'selected' : ''}`}
                onClick={() => onSelectDocument(doc)}
              >
                <div className={`doc-icon ${getFileTypeClass(doc.file_type)}`}>
                  {getFileIcon(doc.file_type)}
                </div>
                <div className="doc-info">
                  <div className="doc-name">{doc.title}</div>
                  <div className="doc-meta">
                    <span className={`doc-status ${doc.processed ? 'processed' : 'pending'}`}>
                      <span className="status-dot" style={{
                        width: 6, height: 6, display: 'inline-block',
                        borderRadius: '50%',
                        background: doc.processed ? 'var(--success)' : 'var(--warning)',
                        boxShadow: doc.processed ? '0 0 6px rgba(34,197,94,0.4)' : '0 0 6px rgba(245,158,11,0.4)'
                      }} />
                      {doc.processed ? 'Processed' : 'Pending'}
                    </span>
                    {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
                  </div>
                </div>
                <div className="doc-actions">
                  {!doc.processed && (
                    <button
                      className="doc-action-btn"
                      onClick={(e) => { e.stopPropagation(); onProcessDocument(doc.id); }}
                      title="Process document"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                      </svg>
                    </button>
                  )}
                  <button
                    className="doc-action-btn danger"
                    onClick={(e) => { e.stopPropagation(); onDeleteDocument(doc.id); }}
                    title="Delete document"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Status Bar */}
      <div className="sidebar-status">
        <div className="status-row">
          <span className="status-label">
            <span className={`status-dot ${ollamaStatus?.running ? 'online' : 'offline'}`} />
            Ollama
          </span>
          <span className="status-value">
            {ollamaStatus?.running 
              ? `v${ollamaStatus.version || ''} ${ollamaStatus.model_count || 0} models`
              : 'Offline'}
          </span>
        </div>
        <div className="status-row">
          <span className="status-label">
            <span className={`status-dot ${vectorStats?.vector?.total_chunks > 0 ? 'online' : 'warning'}`} />
            Vector DB
          </span>
          <span className="status-value">
            {vectorStats?.vector?.total_chunks || 0} chunks
            {vectorStats?.keyword?.total_chunks > 0 ? ` +${vectorStats.keyword.total_chunks} kw` : ''}
          </span>
        </div>
        <div className="status-row">
          <span className="status-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
            Retrieval
          </span>
          <span className="status-value">Hybrid</span>
        </div>
        <div className="status-row">
          <span className="status-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            Model
          </span>
          <span className="status-value">{llmModel || 'Not set'}</span>
        </div>
        <div className="status-row" style={{ justifyContent: 'center' }}>
          <button className="status-refresh-btn" onClick={onRefreshStatus} title="Refresh status">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="23 4 23 10 17 10"/>
              <polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './Chat.css';

export default function Chat({ messages, onSendMessage, isLoading, selectedDoc, onShowSources }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-container">
      {/* Chat Header */}
      {!messages.length ? (
        <div className="chat-welcome">
          <div className="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <h1 className="welcome-title">Document Q&A System</h1>
          <p className="welcome-subtitle">
            Upload a document from the sidebar, then ask questions about its content.
            The system uses RAG (Retrieval-Augmented Generation) to find relevant information
            and generate answers with citations.
          </p>
          <div className="welcome-features">
            <div className="feature-card">
              <div className="feature-icon">📄</div>
              <div className="feature-text">Upload PDF, DOCX, or TXT files</div>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <div className="feature-text">Intelligent context retrieval</div>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <div className="feature-text">AI-powered answers with citations</div>
            </div>
            <div className="feature-card">
              <div className="feature-icon">💬</div>
              <div className="feature-text">Conversational chat with memory</div>
            </div>
          </div>
          {selectedDoc && (
            <div className="active-doc-info">
              Active document: <strong>{selectedDoc.title}</strong>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Messages Area */}
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                      <circle cx="12" cy="7" r="4"/>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2a10 10 0 1 0 10 10h-10V2z"/>
                      <path d="M12 12 20 12"/>
                      <path d="M12 16 16 16"/>
                    </svg>
                  )}
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-sender">
                      {msg.role === 'user' ? 'You' : 'Assistant'}
                    </span>
                    <span className="message-time">
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="message-text">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  
                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="message-sources">
                      <button
                        className="sources-toggle"
                        onClick={() => onShowSources(msg.sources)}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10"/>
                          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                          <line x1="12" y1="17" x2="12.01" y2="17"/>
                        </svg>
                        View {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
                      </button>
                    </div>
                  )}
                  
                  {/* Metadata */}
                  {msg.metadata && (
                    <div className="message-meta">
                      <span className="badge badge-accent">
                        {msg.metadata.latency_ms}ms
                      </span>
                      <span className="badge">
                        {msg.metadata.chunks_retrieved} chunks
                      </span>
                      {msg.metadata.retrieval_method && (
                        <span className={`retrieval-badge ${msg.metadata.retrieval_method.includes('hybrid') ? 'hybrid' : 'vector'}`}>
                          {msg.metadata.retrieval_method.includes('hybrid') ? '🔀 Hybrid' : '📡 Vector'}
                        </span>
                      )}
                      {msg.metadata.embedding_model && (
                        <span className="badge badge-info">
                          {msg.metadata.embedding_model.split('/').pop()}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="message assistant">
                <div className="message-avatar">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2a10 10 0 1 0 10 10h-10V2z"/>
                    <path d="M12 12 20 12"/>
                    <path d="M12 16 16 16"/>
                  </svg>
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-sender">Assistant</span>
                  </div>
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </>
      )}

      {/* Input Area */}
      <div className="chat-input-area">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              className="chat-input"
              placeholder={selectedDoc ? "Ask a question about your document..." : "Upload a document first, then ask questions..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!input.trim() || isLoading}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </form>
        <div className="input-footer">
          RAG-powered answers with source citations. Answers may not be 100% accurate.
        </div>
      </div>
    </div>
  );
}
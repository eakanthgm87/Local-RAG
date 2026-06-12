import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import FileUpload from './components/FileUpload';
import ModelSelector from './components/ModelSelector';
import Citation from './components/Citation';
import * as api from './api';
import './App.css';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [llmProvider, setLlmProvider] = useState('ollama');
  const [llmModel, setLlmModel] = useState('');
  const [useQuantization, setUseQuantization] = useState(true);
  const [ollamaModels, setOllamaModels] = useState([]);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [groqConfigured, setGroqConfigured] = useState(false);
  const [vectorStats, setVectorStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showSources, setShowSources] = useState(null);
  const [statusInfo, setStatusInfo] = useState(null);
  const initialized = useRef(false);

  // Initialize data on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    
    const init = async () => {
      try {
        const [health, sessList, docs, oModels, oStatus, vStats] = await Promise.all([
          api.healthCheck(),
          api.getSessions(),
          api.getDocuments(),
          api.getOllamaModels(),
          api.getOllamaStatus(),
          api.getVectorStatus(),
        ]);
        
        setSessions(sessList);
        setDocuments(docs);
        setOllamaModels(oModels.models || []);
        setOllamaStatus(oStatus);
        setGroqConfigured(health.groq_configured);
        setVectorStats(vStats);
        
        // Set default model
        if (oModels.models && oModels.models.length > 0) {
          setLlmModel(oModels.models[0].name);
        } else {
          setLlmModel('phi4:mini');
        }
      } catch (err) {
        console.error('Init error:', err);
        toast.error('Failed to connect to backend. Make sure the server is running.');
      }
    };
    
    init();
  }, []);

  // Load session messages when switching
  useEffect(() => {
    if (currentSession) {
      api.getSessionMessages(currentSession.id)
        .then(setMessages)
        .catch(() => setMessages([]));
    } else {
      setMessages([]);
    }
  }, [currentSession]);

  // Session management
  const handleNewSession = useCallback(async () => {
    try {
      const session = await api.createSession({ title: 'New Chat' });
      setSessions(prev => [session, ...prev]);
      setCurrentSession(session);
      setMessages([]);
    } catch (err) {
      toast.error('Failed to create session');
    }
  }, []);

  const handleSelectSession = useCallback((session) => {
    setCurrentSession(session);
  }, []);

  const handleDeleteSession = useCallback(async (id) => {
    try {
      await api.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (currentSession?.id === id) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (err) {
      toast.error('Failed to delete session');
    }
  }, [currentSession]);

  // Document management
  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to refresh docs:', err);
    }
  }, []);

  const handleUploadComplete = useCallback((doc) => {
    refreshDocuments();
    // Auto-select the uploaded doc
    setSelectedDoc(doc);
    // Auto-process
    api.processDocument(doc.id).then(result => {
      toast.success(`Document processed: ${result.chunk_count} chunks created`);
      refreshDocuments();
    }).catch(err => {
      toast.error('Failed to process document');
    });
  }, [refreshDocuments]);

  const handleDeleteDocument = useCallback(async (id) => {
    try {
      await api.deleteDocument(id);
      refreshDocuments();
      if (selectedDoc?.id === id) setSelectedDoc(null);
      toast.success('Document deleted');
    } catch (err) {
      toast.error('Failed to delete document');
    }
  }, [selectedDoc, refreshDocuments]);

  const handleProcessDocument = useCallback(async (id) => {
    try {
      const result = await api.processDocument(id);
      toast.success(`Processed: ${result.chunk_count} chunks`);
      refreshDocuments();
    } catch (err) {
      toast.error('Processing failed');
    }
  }, [refreshDocuments]);

  // Ask a question
  const handleSendMessage = useCallback(async (content) => {
    if (!content.trim()) return;
    
    // Add user message to UI immediately
    const userMsg = { id: Date.now(), role: 'user', content, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    
    setIsLoading(true);
    
    try {
      const result = await api.askQuestion({
        question: content,
        session_id: currentSession?.id || null,
        document_id: selectedDoc?.id || null,
        llm_provider: llmProvider,
        llm_model: llmModel,
        use_quantization: useQuantization,
      });
      
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
        metadata: result.metadata,
        created_at: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, assistantMsg]);
      
      // Update current session if new one was created
      if (result.session_id && result.session_id !== currentSession?.id) {
        const sessionsList = await api.getSessions();
        setSessions(sessionsList);
        const newSession = sessionsList.find(s => s.id === result.session_id);
        if (newSession) setCurrentSession(newSession);
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to get answer');
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, selectedDoc, llmProvider, llmModel, useQuantization]);

  // Model management
  const handlePullModel = useCallback(async (modelName) => {
    try {
      toast.loading(`Downloading ${modelName}...`);
      await api.pullOllamaModel(modelName);
      toast.dismiss();
      toast.success(`Model ${modelName} downloaded!`);
      
      const oModels = await api.getOllamaModels();
      setOllamaModels(oModels.models || []);
    } catch (err) {
      toast.dismiss();
      toast.error('Failed to download model');
    }
  }, []);

  const handleRefreshStatus = useCallback(async () => {
    const [oStatus, oModels, vStats] = await Promise.all([
      api.getOllamaStatus(),
      api.getOllamaModels(),
      api.getVectorStatus(),
    ]);
    setOllamaStatus(oStatus);
    setOllamaModels(oModels.models || []);
    setVectorStats(vStats);
  }, []);

  return (
    <div className="app">
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius)',
          },
        }}
      />
      
      <Sidebar
        sessions={sessions}
        currentSession={currentSession}
        documents={documents}
        selectedDoc={selectedDoc}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onSelectDocument={setSelectedDoc}
        onDeleteDocument={handleDeleteDocument}
        onProcessDocument={handleProcessDocument}
        onUploadClick={() => setShowFileUpload(true)}
        onModelSelectorClick={() => setShowModelSelector(true)}
        onRefreshStatus={handleRefreshStatus}
        ollamaStatus={ollamaStatus}
        vectorStats={vectorStats}
        llmProvider={llmProvider}
        llmModel={llmModel}
        groqConfigured={groqConfigured}
      />
      
      <main className="main-content">
        <Chat
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          selectedDoc={selectedDoc}
          onShowSources={setShowSources}
        />
      </main>
      
      {showFileUpload && (
        <FileUpload
          onClose={() => setShowFileUpload(false)}
          onUploadComplete={handleUploadComplete}
        />
      )}
      
      {showModelSelector && (
        <ModelSelector
          onClose={() => setShowModelSelector(false)}
          ollamaModels={ollamaModels}
          ollamaStatus={ollamaStatus}
          groqConfigured={groqConfigured}
          llmProvider={llmProvider}
          llmModel={llmModel}
          useQuantization={useQuantization}
          onProviderChange={setLlmProvider}
          onModelChange={setLlmModel}
          onQuantizationChange={setUseQuantization}
          onPullModel={handlePullModel}
          onRefreshStatus={handleRefreshStatus}
        />
      )}
      
      {showSources && (
        <div className="modal-overlay" onClick={() => setShowSources(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Sources</h3>
              <button className="btn-icon" onClick={() => setShowSources(null)}>✕</button>
            </div>
            <div className="modal-body">
              {showSources.map((source, i) => (
                <Citation key={i} source={source} index={i} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
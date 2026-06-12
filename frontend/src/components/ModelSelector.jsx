import React, { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import * as api from '../api';
import './ModelSelector.css';

export default function ModelSelector({
  onClose,
  ollamaModels,
  ollamaStatus,
  groqConfigured,
  llmProvider,
  llmModel,
  useQuantization,
  onProviderChange,
  onModelChange,
  onQuantizationChange,
  onPullModel,
  onRefreshStatus,
}) {
  const [serverActionLoading, setServerActionLoading] = useState(null); // null | 'start' | 'stop'
  const [modelActionLoading, setModelActionLoading] = useState(null);
  const [localRunning, setLocalRunning] = useState(new Set());

  // Merge backend running_models with optimistic local running state
  const runningModels = new Set([
    ...(ollamaStatus?.running_models || []),
    ...localRunning,
  ]);

  const isModelRunning = useCallback((modelName) => {
    return runningModels.has(modelName);
  }, [runningModels]);

  const formatSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const gb = bytes / (1024 * 1024 * 1024);
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
  };

  // Server actions with optimistic UI
  const handleStartOllama = async () => {
    setServerActionLoading('start');
    try {
      const result = await api.ollamaAction('start');
      if (result.success) {
        toast.success(result.message || 'Ollama started');
      } else {
        toast.error(result.message || 'Failed to start Ollama');
      }
    } catch { toast.error('Failed to start Ollama'); }
    finally {
      setServerActionLoading(null);
      if (onRefreshStatus) onRefreshStatus();
    }
  };

  const handleStopOllama = async () => {
    setServerActionLoading('stop');
    try {
      const result = await api.ollamaAction('stop');
      if (result.success) {
        toast.success(result.message || 'Ollama stopped');
      } else {
        toast.error(result.message || 'Failed to stop Ollama');
      }
    } catch { toast.error('Failed to stop Ollama'); }
    finally {
      setServerActionLoading(null);
      setLocalRunning(new Set());
      if (onRefreshStatus) onRefreshStatus();
    }
  };

  // Model actions with immediate feedback
  const handleRunModel = async (modelName) => {
    setModelActionLoading('run_' + modelName);
    // Optimistically mark as running
    setLocalRunning(prev => new Set([...prev, modelName]));
    try {
      const result = await api.ollamaAction('run_model', modelName);
      if (result.success) {
        toast.success(result.message || `Model ${modelName} loaded`);
      } else {
        toast.error(result.message || `Failed to load ${modelName}`);
        // Revert optimistic state on failure
        setLocalRunning(prev => { const s = new Set(prev); s.delete(modelName); return s; });
      }
    } catch {
      toast.error('Failed to run model');
      setLocalRunning(prev => { const s = new Set(prev); s.delete(modelName); return s; });
    } finally {
      setModelActionLoading(null);
      if (onRefreshStatus) onRefreshStatus();
    }
  };

  const handleStopModel = async (modelName) => {
    setModelActionLoading('stop_' + modelName);
    // Optimistically mark as stopped
    setLocalRunning(prev => { const s = new Set(prev); s.delete(modelName); return s; });
    try {
      const result = await api.ollamaAction('stop_model', modelName);
      if (result.success) {
        toast.success(result.message || `Model ${modelName} unloaded`);
      } else {
        toast.error(result.message || `Failed to unload ${modelName}`);
        // Revert optimistic state on failure
        setLocalRunning(prev => new Set([...prev, modelName]));
      }
    } catch {
      toast.error('Failed to stop model');
      setLocalRunning(prev => new Set([...prev, modelName]));
    } finally {
      setModelActionLoading(null);
      if (onRefreshStatus) onRefreshStatus();
    }
  };

  const handleRemoveModel = async (modelName) => {
    if (!window.confirm(`Delete "${modelName}" from disk?`)) return;
    setModelActionLoading('del_' + modelName);
    try {
      const result = await api.ollamaAction('remove_model', modelName);
      toast[result.success ? 'success' : 'error'](result.message || `Model ${modelName} removed`);
      if (onRefreshStatus) setTimeout(onRefreshStatus, 2000);
    } catch { toast.error('Failed to remove model'); }
    finally { setModelActionLoading(null); }
  };

  const handlePullModel = async (modelName) => {
    setModelActionLoading('pull_' + modelName);
    try {
      toast.loading(`Downloading ${modelName}...`);
      await api.pullOllamaModel(modelName);
      toast.dismiss();
      toast.success(`${modelName} downloaded!`);
      if (onRefreshStatus) setTimeout(onRefreshStatus, 2000);
    } catch { toast.dismiss(); toast.error('Download failed'); }
    finally { setModelActionLoading(null); }
  };

  const isLoading = (action, name) => modelActionLoading === action + '_' + name;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content model-selector" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Settings</h3>
          <button className="btn-icon" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">

          {/* ===== SECTION 1: OLLAMA SERVER ===== */}
          <div className="setting-group">
            <label className="setting-label">Ollama Server</label>
            <div className="ollama-server-control">
              <div className="server-info-row">
                <span className={`badge ${ollamaStatus?.running ? 'badge-success' : 'badge-danger'}`}
                      style={{ fontSize: '13px', padding: '4px 12px' }}>
                  {ollamaStatus?.running ? '● Running' : '○ Stopped'}
                </span>
                <span className="badge">{ollamaStatus?.installed ? 'Installed' : 'Not Found'}</span>
                {ollamaStatus?.version && <span className="badge badge-accent">v{ollamaStatus.version}</span>}
              </div>
              <div className="server-actions">
                <button className="btn btn-success" onClick={handleStartOllama}
                  disabled={serverActionLoading === 'start' || serverActionLoading === 'stop' || ollamaStatus?.running}>
                  {serverActionLoading === 'start' ? <><span className="spinner" style={{width:14,height:14}} /> Starting...</> : '▶ Start'}
                </button>
                <button className="btn btn-danger" onClick={handleStopOllama}
                  disabled={serverActionLoading === 'start' || serverActionLoading === 'stop' || !ollamaStatus?.running}>
                  {serverActionLoading === 'stop' ? <><span className="spinner" style={{width:14,height:14}} /> Stopping...</> : '■ Stop'}
                </button>
                <button className="btn" onClick={() => { if (onRefreshStatus) onRefreshStatus(); }}
                  disabled={serverActionLoading !== null}>
                  ⟳ Refresh
                </button>
              </div>
              {!ollamaStatus?.installed && (
                <div className="status-message warning" style={{marginTop:10}}>
                  <span>⚠️</span>
                  <span>Ollama not installed. Get it at <a href="https://ollama.com" target="_blank" rel="noreferrer">ollama.com</a></span>
                </div>
              )}
            </div>
          </div>

          {/* ===== SECTION 2: MODELS ===== */}
          <div className="setting-group">
            <label className="setting-label" style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
              <span>Models</span>
              <span className="badge">{ollamaModels.length} installed</span>
            </label>

            {!ollamaStatus?.running ? (
              <div className="status-message warning">
                <span>⚠️</span><span>Start Ollama server above to manage models.</span>
              </div>
            ) : ollamaModels.length === 0 ? (
              <div className="status-message info">
                <span>ℹ️</span><span>No models yet. Pull one below.</span>
              </div>
            ) : (
              <div className="model-list">
                {ollamaModels.map((model) => (
                  <div key={model.name} className="model-item">
                    <div className="model-info" onClick={() => onModelChange(model.name)}>
                      <div className="model-name-row">
                        <span className="model-name">{model.name}</span>
                        {isModelRunning(model.name) && <span className="running-tag">● Loaded</span>}
                        {llmModel === model.name && <span className="active-tag">Active</span>}
                      </div>
                      <div className="model-details">
                        <span className="badge">{formatSize(model.size)}</span>
                        {model.quantized && <span className="badge badge-accent">Q4</span>}
                        {model.ram_requirement_gb && (
                          <span className="badge badge-warning">~{model.ram_requirement_gb}GB RAM</span>
                        )}
                      </div>
                    </div>
                    <div className="model-actions">
                      <button className={`model-action-btn run-btn ${isModelRunning(model.name) ? 'active' : ''}`}
                        onClick={() => handleRunModel(model.name)}
                        disabled={isLoading('run', model.name) || isLoading('stop', model.name) || isModelRunning(model.name)}
                        title="Load into memory">
                        {isLoading('run', model.name) ? '...' : '▶'}
                      </button>
                      <button className="model-action-btn stop-btn"
                        onClick={() => handleStopModel(model.name)}
                        disabled={isLoading('stop', model.name) || isLoading('run', model.name) || !isModelRunning(model.name)}
                        title="Unload from memory">
                        {isLoading('stop', model.name) ? '...' : '⏹'}
                      </button>
                      <button className="model-action-btn del-btn"
                        onClick={() => handleRemoveModel(model.name)}
                        disabled={isLoading('del', model.name) || isModelRunning(model.name)}
                        title="Delete from disk">
                        {isLoading('del', model.name) ? '...' : '🗑'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Quick pull */}
            <div style={{marginTop:14}}>
              <label className="setting-label" style={{fontSize:12, color:'var(--text-muted)', marginBottom:8}}>
                Download Models
              </label>
              <div className="quick-pull-list">
                {['phi4:mini', 'llama3.2:3b', 'llama3.2:1b', 'qwen2.5:1.5b', 'gemma2:2b', 'mistral:7b'].map((m) => (
                  <button key={m} className="quick-pull-btn"
                    onClick={() => handlePullModel(m)}
                    disabled={!ollamaStatus?.running || isLoading('pull', m)}>
                    {isLoading('pull', m) ? '...' : `⬇ ${m}`}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* ===== SECTION 3: LLM PROVIDER ===== */}
          <div className="setting-group">
            <label className="setting-label">LLM Provider</label>
            <div className="provider-options">
              <button className={`provider-btn ${llmProvider === 'ollama' ? 'active' : ''}`}
                onClick={() => onProviderChange('ollama')}>
                <div className="provider-name">Ollama (Local)</div>
                <div className="provider-desc">Run models on your CPU/GPU</div>
                <span className={`badge ${ollamaStatus?.running ? 'badge-success' : 'badge-danger'}`}>
                  {ollamaStatus?.running ? 'Connected' : 'Offline'}
                </span>
              </button>
              <button className={`provider-btn ${llmProvider === 'groq' ? 'active' : ''}`}
                onClick={() => onProviderChange('groq')} disabled={!groqConfigured}>
                <div className="provider-name">Groq API (Cloud)</div>
                <div className="provider-desc">Fast cloud inference (free)</div>
                <span className={`badge ${groqConfigured ? 'badge-success' : 'badge-warning'}`}>
                  {groqConfigured ? 'Ready' : 'No API Key'}
                </span>
              </button>
            </div>
          </div>

          {/* ===== SECTION 4: QUANTIZATION ===== */}
          <div className="setting-group">
            <div className="toggle-row">
              <div>
                <label className="setting-label">Quantization</label>
                <div className="setting-desc">
                  Uses GGUF Q4_K_M for faster CPU inference with ~75% less RAM.
                </div>
              </div>
              <label className="toggle">
                <input type="checkbox" checked={useQuantization}
                  onChange={(e) => onQuantizationChange(e.target.checked)} />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>

          {/* ===== SECTION 5: RAM GUIDE ===== */}
          <div className="setting-group">
            <label className="setting-label" style={{fontSize:12, color:'var(--text-muted)'}}>
              RAM Recommendations
            </label>
            <div className="ram-guide" style={{marginTop:6}}>
              <div className="ram-item">
                <span className="ram-range">{'< 4GB'}</span>
                <span className="ram-models">qwen2.5:0.5b, llama3.2:1b, phi4:mini</span>
              </div>
              <div className="ram-item">
                <span className="ram-range">4-8GB</span>
                <span className="ram-models">llama3.2:3b, qwen2.5:3b, gemma2:2b</span>
              </div>
              <div className="ram-item">
                <span className="ram-range">8-16GB</span>
                <span className="ram-models">mistral:7b, qwen2.5:7b, llama3.1:8b</span>
              </div>
              <div className="ram-item">
                <span className="ram-range">16GB+</span>
                <span className="ram-models">phi4:14b, deepseek-r1:14b</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
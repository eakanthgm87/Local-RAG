import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check
export const healthCheck = () => api.get('/health/').then(res => res.data);

// Documents
export const getDocuments = () => api.get('/documents/').then(res => res.data);
export const getDocument = (id) => api.get(`/documents/${id}/`).then(res => res.data);
export const uploadDocument = (formData) => api.post('/documents/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
}).then(res => res.data);
export const deleteDocument = (id) => api.delete(`/documents/${id}/`).then(res => res.data);
export const processDocument = (id) => api.post(`/documents/${id}/process/`).then(res => res.data);
export const downloadDocument = (id) => api.get(`/documents/${id}/download/`, {
  responseType: 'blob',
}).then(res => res.data);

// Chat Sessions
export const getSessions = () => api.get('/sessions/').then(res => res.data);
export const getSession = (id) => api.get(`/sessions/${id}/`).then(res => res.data);
export const createSession = (data) => api.post('/sessions/', data).then(res => res.data);
export const updateSession = (id, data) => api.patch(`/sessions/${id}/`, data).then(res => res.data);
export const deleteSession = (id) => api.delete(`/sessions/${id}/`).then(res => res.data);
export const getSessionMessages = (id) => api.get(`/sessions/${id}/messages/`).then(res => res.data);
export const addSessionMessage = (id, data) => api.post(`/sessions/${id}/messages/`, data).then(res => res.data);

// Q&A
export const askQuestion = (data) => api.post('/ask/', data).then(res => res.data);

// Models
export const getOllamaModels = () => api.get('/models/ollama/').then(res => res.data);
export const getGroqModels = () => api.get('/models/groq/').then(res => res.data);
export const pullOllamaModel = (model) => api.post('/models/ollama/pull/', { model }).then(res => res.data);

// Ollama Server Management (start/stop server, run/stop/remove models)
export const getOllamaStatus = () => api.get('/status/ollama/').then(res => res.data);
export const ollamaAction = (action, model = null) => {
  const data = { action };
  if (model) data.model = model;
  return api.post('/status/ollama/', data).then(res => res.data);
};
export const ollamaStopServer = () => api.delete('/status/ollama/').then(res => res.data);

// Vector DB
export const getVectorStatus = () => api.get('/status/vector/').then(res => res.data);

// Logs
export const getQueryLogs = () => api.get('/logs/').then(res => res.data);

export default api;
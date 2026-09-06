/**
 * Axios client — backend API base config.
 * API keys are NEVER included here — all auth is via JWT.
 */
import axios from 'axios';

const apiClient = axios.create({
  // CRA exposes env vars as process.env.REACT_APP_* (never import.meta.env)
  baseURL: process.env.REACT_APP_API_URL ?? '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT from localStorage on every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;

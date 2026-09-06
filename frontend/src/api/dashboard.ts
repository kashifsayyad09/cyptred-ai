/**
 * Dashboard API — typed wrappers around backend endpoints.
 * All requests are authenticated via JWT (set in client.ts interceptor).
 * API keys are NEVER included here.
 */

import apiClient from './client';
import type {
  ExamSession,
  TimelineEvent,
  ExplanationResponse,
  ProviderHealthStatus,
  RiskScore,
} from '../types';

// ── Sessions ──────────────────────────────────────────────────────────────────

export async function fetchSessions(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ExamSession[]> {
  const res = await apiClient.get('/sessions', { params });
  return res.data.sessions ?? res.data ?? [];
}

export async function fetchSession(sessionId: string): Promise<ExamSession> {
  const res = await apiClient.get(`/sessions/${sessionId}`);
  return res.data;
}

// ── Events / timeline ─────────────────────────────────────────────────────────

export async function fetchSessionEvents(sessionId: string): Promise<TimelineEvent[]> {
  const res = await apiClient.get(`/events`, { params: { session_id: sessionId } });
  return res.data.events ?? res.data ?? [];
}

// ── Risk ──────────────────────────────────────────────────────────────────────

export async function fetchLatestRisk(sessionId: string): Promise<RiskScore> {
  const res = await apiClient.get(`/risk/${sessionId}/latest`);
  return res.data;
}

// ── AI Explanation ────────────────────────────────────────────────────────────

export async function requestExplanation(payload: {
  session_id: string;
  exam_title: string;
  risk_score: number;
  risk_level: string;
  events: Record<string, unknown>[];
  policy_context?: string;
  incident_summary?: string;
}): Promise<ExplanationResponse> {
  const res = await apiClient.post('/explain', payload);
  return res.data;
}

// ── Provider health ───────────────────────────────────────────────────────────

export async function fetchProviderHealth(): Promise<ProviderHealthStatus> {
  const res = await apiClient.get('/explain/provider-health');
  return res.data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.set('username', email);
  form.set('password', password);
  const res = await apiClient.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  const token: string = res.data.access_token;
  localStorage.setItem('access_token', token);
  return token;
}

export function logout(): void {
  localStorage.removeItem('access_token');
}

export function isLoggedIn(): boolean {
  return Boolean(localStorage.getItem('access_token'));
}

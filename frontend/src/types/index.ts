/** Shared TypeScript types for AI Exam Guardian */

export type RiskLevel =
  | 'NORMAL'
  | 'MONITORING'
  | 'ATTENTION'
  | 'REVIEW_REQUIRED'
  | 'HIGH_PRIORITY_REVIEW';

export type DetectionState = 'DETECTED' | 'SUSPECTED' | 'NOT_DETECTED' | 'UNOBSERVABLE';

export type SessionStatus = 'active' | 'completed' | 'flagged';

export interface ExamSession {
  id: string;
  examId: string;
  examTitle: string;
  studentId: string;
  studentName: string;
  startedAt: string;
  endedAt?: string;
  riskScore: number;
  riskLevel: RiskLevel;
  aiDetectionState: DetectionState;
  eventCount: number;
  status: SessionStatus;
}

export interface TimelineEvent {
  id: string;
  sessionId: string;
  occurred_at: string;
  event_type: string;
  source: string;
  rule: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  score_contribution: number;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface AIDetectionSignal {
  assistant_name: string;
  detection_state: DetectionState;
  confidence: number;
}

export interface RiskScore {
  session_id: string;
  score: number;
  risk_level: RiskLevel;
  scored_at: string;
  event_count: number;
}

export interface ExplanationResponse {
  session_id: string;
  explanation: string;
  teacher_disclaimer: string;
  provider: string;
  is_fallback: boolean;
  latency_ms: number;
  success: boolean;
  degraded: boolean;
  has_evidence_label: boolean;
  has_policy_label: boolean;
  has_inference_label: boolean;
  has_disclaimer: boolean;
  mcp_summary_available: boolean;
  rag_policy_available: boolean;
}

export interface ProviderHealth {
  provider: string;
  state: 'healthy' | 'degraded' | 'unhealthy';
  consecutive_failures: number;
  consecutive_successes: number;
  total_requests: number;
  total_failures: number;
  last_failure_at: number | null;
  last_success_at: number | null;
}

export interface ProviderHealthStatus {
  groq: ProviderHealth;
  nvidia: ProviderHealth;
  active_primary: string;
}

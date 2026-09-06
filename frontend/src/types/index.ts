/** Shared TypeScript types for AI Exam Guardian */

export type RiskLevel = 'NORMAL' | 'MONITORING' | 'ATTENTION' | 'REVIEW_REQUIRED' | 'HIGH_PRIORITY_REVIEW';

export type DetectionState = 'DETECTED' | 'SUSPECTED' | 'NOT_DETECTED' | 'UNOBSERVABLE';

export interface ExamSession {
  id: string;
  examId: string;
  studentId: string;
  studentName: string;
  startedAt: string;
  riskScore: number;
  riskLevel: RiskLevel;
  aiDetectionState: DetectionState;
  eventCount: number;
  status: 'active' | 'completed' | 'flagged';
}

export interface TimelineEvent {
  id: string;
  sessionId: string;
  timestamp: string;
  eventType: string;
  source: string;
  rule: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  scoreContribution: number;
  confidence: number;
  metadata: Record<string, unknown>;
}

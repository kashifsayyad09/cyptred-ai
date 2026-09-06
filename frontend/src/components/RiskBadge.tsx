/**
 * RiskBadge — displays a risk level with colour-coded pill styling.
 * Uses CSS custom properties from globals.css for risk colours.
 */

import React from 'react';
import type { RiskLevel } from '../types';

const RISK_CONFIG: Record<
  RiskLevel,
  { label: string; color: string; bg: string }
> = {
  NORMAL:              { label: 'Normal',              color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
  MONITORING:          { label: 'Monitoring',          color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  ATTENTION:           { label: 'Attention',           color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  REVIEW_REQUIRED:     { label: 'Review Required',     color: '#f97316', bg: 'rgba(249,115,22,0.12)' },
  HIGH_PRIORITY_REVIEW:{ label: 'High Priority',       color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
};

interface Props {
  level: RiskLevel;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
}

const RiskBadge: React.FC<Props> = ({ level, score, size = 'md' }) => {
  const cfg = RISK_CONFIG[level] ?? RISK_CONFIG.NORMAL;
  const fontSize = size === 'sm' ? '11px' : size === 'lg' ? '14px' : '12px';
  const padding  = size === 'sm' ? '2px 8px' : size === 'lg' ? '5px 14px' : '3px 10px';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.color}40`,
        borderRadius: '20px',
        fontSize,
        fontWeight: 600,
        padding,
        whiteSpace: 'nowrap',
        letterSpacing: '0.02em',
      }}
    >
      <span
        style={{
          width: size === 'sm' ? 6 : 8,
          height: size === 'sm' ? 6 : 8,
          borderRadius: '50%',
          background: cfg.color,
          flexShrink: 0,
        }}
      />
      {cfg.label}
      {score !== undefined && (
        <span style={{ opacity: 0.8, fontWeight: 400 }}>{score}</span>
      )}
    </span>
  );
};

export default RiskBadge;

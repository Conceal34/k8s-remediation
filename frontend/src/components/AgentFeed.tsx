import { API_BASE } from '../api';
import React, { useEffect, useRef, useState } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────
type PipelineEvent =
  | { type: 'connected' }
  | { type: 'anomaly_detected'; anomaly_id: number; service: string; severity: string; score: number; detected_at: string | null }
  | { type: 'diagnosis';        anomaly_id: number; service: string; text: string }
  | { type: 'remediation';      anomaly_id: number; service: string; proposal: { round: number; action: string; justification: string; confidence: number } }
  | { type: 'critic';           anomaly_id: number; service: string; verdict: { round: number; verdict: string; reason: string } }
  | { type: 'outcome';          anomaly_id: number; service: string | null; outcome: string | null; action: string | null; confidence: number | null }
  | { type: 'error';            anomaly_id: number; service: string; message: string };

interface FeedState {
  anomaly:    Extract<PipelineEvent, { type: 'anomaly_detected' }> | null;
  diagnosis:  string | null;
  proposals:  Extract<PipelineEvent, { type: 'remediation' }>['proposal'][];
  verdicts:   Extract<PipelineEvent, { type: 'critic' }>['verdict'][];
  outcome:    Extract<PipelineEvent, { type: 'outcome' }> | null;
  error:      string | null;
  stage:      'idle' | 'detecting' | 'diagnosing' | 'remediating' | 'reviewing' | 'done' | 'error';
}

const EMPTY: FeedState = {
  anomaly: null, diagnosis: null, proposals: [], verdicts: [],
  outcome: null, error: null, stage: 'idle',
};

// ── helpers ────────────────────────────────────────────────────────────────
const sevColor = (s?: string) =>
  s === 'critical' ? 'var(--color-danger)' : s === 'high' ? 'var(--color-warning)' : 'var(--color-info)';

const Block = ({ emoji, title, accent = 'var(--border-subtle)', children }: {
  emoji: string; title: string; accent?: string; children: React.ReactNode;
}) => (
  <div style={{
    background: 'var(--bg-elevated)',
    border: `1px solid var(--border-subtle)`,
    borderLeft: `3px solid ${accent}`,
    borderRadius: 'var(--radius-sm)',
    padding: 'var(--space-md)',
    animation: 'feedIn 0.35s ease',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '6px' }}>
      <span style={{ fontSize: '0.9rem' }}>{emoji}</span>
      <strong style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {title}
      </strong>
    </div>
    <div style={{ fontSize: '0.79rem', color: 'var(--text-muted)', lineHeight: '1.55', wordBreak: 'break-word', whiteSpace: 'pre-wrap', overflowWrap: 'break-word' }}>
      {children}
    </div>
  </div>
);

const Spinner = ({ label }: { label: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '7px', color: 'var(--text-tertiary)', fontSize: '0.76rem', padding: '2px 0' }}>
    <span className="spin-icon">⟳</span>{label}
  </div>
);

// ── main ───────────────────────────────────────────────────────────────────
export default function AgentFeed({ activeAnomaliesCount = 0 }: { activeAnomaliesCount?: number }) {
  const [feed, setFeed]         = useState<FeedState>(EMPTY);
  const [cleared, setCleared]   = useState<number | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  // Fallback: if feed is still empty 5s after SSE connects, poll /decisions/ to rebuild it from DB.
  // This ensures the feed always shows the last known state even if SSE events were missed.
  useEffect(() => {
    if (!connected || feed.anomaly) return; // SSE working fine or already populated
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/decisions/`);
        const data = await res.json();
        if (!data || !data[0]) return;
        const d = data[0]; // Most recent decision
        const anomalyData = d.anomaly;
        if (!anomalyData) return;
        // Rebuild feed from DB data
        setFeed({
          anomaly: {
            type: 'anomaly_detected',
            anomaly_id: anomalyData.id,
            service: d.service,
            severity: anomalyData.severity,
            score: anomalyData.score,
            detected_at: anomalyData.detected_at,
          },
          diagnosis: d.diagnosis_text || null,
          proposals: (d.remediation_proposals || []).map((p: any) => ({ ...p })),
          verdicts: (d.critic_verdicts || []).map((v: any) => ({ ...v })),
          outcome: d.autonomy_outcome ? {
            type: 'outcome',
            anomaly_id: anomalyData.id,
            service: d.service,
            outcome: d.autonomy_outcome,
            action: d.final_action,
            confidence: d.confidence_score,
          } : null,
          error: d.pipeline_error || null,
          stage: 'done',
        });
        console.log('[Feed] Rebuilt from DB fallback — decision ID:', d.id);
      } catch (e) {
        console.warn('[Feed] DB fallback fetch failed:', e);
      }
    }, 5000); // Wait 5s for SSE to deliver events first
    return () => clearTimeout(timer);
  }, [connected, feed.anomaly]);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/sse/pipeline-feed`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (ev) => {
      let event: PipelineEvent;
      try {
        event = JSON.parse(ev.data);
      } catch (err) {
        return;
      }
      
      console.log('[SSE Event Received]:', event.type, event);

      if (event.type === 'connected') { setConnected(true); return; }

      setFeed(prev => {
        switch (event.type) {
          case 'anomaly_detected':
            // New anomaly → wipe previous state
            return { ...EMPTY, anomaly: event, stage: 'diagnosing' };

          case 'diagnosis':
            return { ...prev, diagnosis: event.text, stage: 'remediating' };

          case 'remediation':
            return { ...prev, proposals: [...prev.proposals, event.proposal], stage: 'reviewing' };

          case 'critic':
            return { ...prev, verdicts: [...prev.verdicts, event.verdict], stage: 'reviewing' };

          case 'outcome':
            return { ...prev, outcome: event, stage: 'done' };

          case 'error':
            return { ...prev, error: event.message, stage: 'error' };

          default:
            return prev;
        }
      });
    };

    return () => { es.close(); };
  }, []);

  const isCleared = feed.anomaly && feed.anomaly.anomaly_id === cleared;

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* header */}
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="card-title">Live Intelligence Feed</h2>
          <span style={{ fontSize: '0.71rem', color: 'var(--text-muted)' }}>
            {connected
              ? <span style={{ color: 'var(--color-success)' }}>● SSE connected</span>
              : <span style={{ color: 'var(--color-danger)' }}>○ reconnecting…</span>}
            &nbsp;· Gemini + Isolation Forest
          </span>
        </div>
        <button className="btn-ghost" style={{ fontSize: '0.71rem', padding: '4px 10px' }}
          onClick={() => { if (feed.anomaly) setCleared(feed.anomaly.anomaly_id); }}>
          Clear ✕
        </button>
      </div>

      {/* body */}
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '0 var(--space-lg) var(--space-lg)',
        display: 'flex', flexDirection: 'column', gap: '10px',
      }}>
        {(!feed.anomaly || isCleared) ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', marginTop: '2rem' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🛰️</div>
            Monitoring cluster — waiting for anomaly…
          </div>
        ) : (
          <>
            {/* ── Detection ── */}
            <Block emoji="🌲" title="Isolation Forest — Detection" accent={sevColor(feed.anomaly.severity)}>
              Anomaly on <code style={{ color: 'var(--accent-primary)' }}>{feed.anomaly.service}</code>
              {' '}· Severity{' '}
              <strong style={{ color: sevColor(feed.anomaly.severity) }}>{feed.anomaly.severity?.toUpperCase()}</strong>
              {' '}· Score{' '}
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>{feed.anomaly.score.toFixed(3)}</span>
              <br />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                {feed.anomaly.detected_at ? new Date(feed.anomaly.detected_at).toLocaleTimeString() : '—'}
              </span>
            </Block>

            {/* ── Diagnosis ── */}
            {feed.stage === 'diagnosing' && !feed.diagnosis && <Spinner label="Diagnosis Agent thinking…" />}
            {feed.stage === 'remediating' && <Spinner label="Remediation Agent formulating plan…" />}
            {feed.stage === 'reviewing' && <Spinner label="Critic Agent evaluating proposal…" />}
            {feed.diagnosis && (
              <Block emoji="🧠" title="Diagnosis Agent — Gemini" accent="var(--accent-primary)">
                {feed.diagnosis}
              </Block>
            )}

            {/* ── Remediation & Critic Rounds ── */}
            {feed.proposals.map((p, idx) => {
              const v = feed.verdicts.find(x => x.round === p.round);
              return (
                <React.Fragment key={idx}>
                  <Block emoji="🛠️" title={`Remediation Agent — Round ${p.round}`} accent="var(--color-info)">
                    Action: <strong style={{ color: 'var(--text-primary)' }}>{p.action}</strong>
                    <br />
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)' }}>{p.justification}</span>
                  </Block>
                  {v && (
                    <Block emoji="⚖️" title={`Critic Agent — Round ${v.round}`}
                      accent={v.verdict === 'APPROVE' ? 'var(--color-success)' : 'var(--color-warning)'}>
                      Verdict:{' '}
                      <strong style={{ color: v.verdict === 'APPROVE' ? 'var(--color-success)' : 'var(--color-warning)' }}>
                        {v.verdict}
                      </strong>
                      {'confidence' in v && v.confidence !== undefined && (
                        <>
                          {' '}· Confidence: <strong style={{ color: 'var(--color-success)' }}>{Math.round((v as any).confidence * 100)}%</strong>
                        </>
                      )}
                      <br />
                      <span style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)' }}>{v.reason}</span>
                    </Block>
                  )}
                </React.Fragment>
              );
            })}

            {/* ── Error ── */}
            {feed.error && (
              <Block emoji="❌" title="Pipeline Error" accent="var(--color-danger)">
                {feed.error}
              </Block>
            )}

            {/* ── Outcome ── */}
            {feed.outcome && (
              <div style={{
                textAlign: 'center', padding: '10px',
                borderRadius: 'var(--radius-sm)',
                background: feed.outcome.outcome === 'auto_executed' ? 'var(--color-success-dim)' : 'rgba(255,170,0,0.1)',
                color: feed.outcome.outcome === 'auto_executed' ? 'var(--color-success)' : 'var(--color-warning)',
                fontWeight: 600, fontSize: '0.82rem',
                animation: 'feedIn 0.4s ease',
              }}>
                {feed.outcome.outcome === 'auto_executed' ? '✅ Auto-Executed' : '⚠️ Escalated to Operator'}
                {feed.outcome.action && (
                  <span style={{ fontWeight: 400, marginLeft: '8px', color: 'inherit', opacity: 0.75 }}>
                    · {feed.outcome.action}
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes feedIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .spin-icon { display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

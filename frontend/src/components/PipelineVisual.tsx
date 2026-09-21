import { API_BASE } from '../api';
import React, { useEffect, useState } from 'react';
import { getDecisions } from '../api';

type Stage = 'idle' | 'collecting' | 'detecting' | 'diagnosing' | 'remediating' | 'critic' | 'policy' | 'done' | 'escalated' | 'error';

function deriveStage(decisions: any[]): Stage {
  if (!decisions || decisions.length === 0) return 'collecting';

  const latest = decisions[0];
  const outcome = latest.autonomy_outcome || '';
  const error   = latest.pipeline_error;

  if (error) return 'error';
  if (outcome === 'escalated') return 'escalated';
  if (outcome === 'auto_executed') return 'done';

  const rounds = latest.round_count || 0;
  const diagnosis = latest.diagnosis_text;

  if (!diagnosis || diagnosis === 'Pipeline error - no diagnosis.') return 'diagnosing';
  if (rounds === 0) return 'remediating';
  const lastVerdict = latest.critic_verdicts?.[latest.critic_verdicts.length - 1]?.verdict;
  if (lastVerdict === 'REVISE') return 'remediating';
  if (lastVerdict === 'APPROVE' && !outcome) return 'policy';

  return 'done';
}

interface StageProps {
  current: Stage;
  name: 'collecting' | 'detecting' | 'diagnosing' | 'remediating' | 'critic' | 'policy';
  label: string;
  subLabel: string;
  icon: React.ReactNode;
}

const STAGE_ORDER: Stage[] = ['collecting', 'detecting', 'diagnosing', 'remediating', 'critic', 'policy'];

function getStageClass(stageName: StageProps['name'], current: Stage): string {
  const stageIdx = STAGE_ORDER.indexOf(stageName);

  // All stages green when pipeline completed successfully
  if (current === 'done') {
    return 'completed';
  }

  // Idle — nothing active yet
  if (current === 'idle') {
    return '';
  }

  if (current === 'error') {
    const errorIdx = STAGE_ORDER.indexOf('diagnosing');
    if (stageIdx < errorIdx) return 'completed';
    if (stageIdx === errorIdx) return 'error';
    return '';
  }
  
  if (current === 'escalated') {
    const policyIdx = STAGE_ORDER.indexOf('policy');
    return stageIdx <= policyIdx ? 'completed' : '';
  }
  
  const currentIdx = STAGE_ORDER.indexOf(current as any);
  if (stageIdx < currentIdx) return 'completed';
  if (stageIdx === currentIdx) return 'active';
  return '';
}

function getStatusLabel(stageName: StageProps['name'], current: Stage, subLabel: string): string {
  const cls = getStageClass(stageName, current);
  if (current === 'error' && stageName === 'diagnosing') return 'Error!';
  if (current === 'escalated' && stageName === 'policy') return 'Escalated';
  if (cls === 'active') return current === 'diagnosing' ? 'Processing…' : 'Running…';
  if (cls === 'completed') return 'Done ✓';
  return subLabel;
}

export default function PipelineVisual({ activeAnomaliesCount = 0 }: { activeAnomaliesCount?: number }) {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [lastFetch, setLastFetch] = useState<string>('—');
  const [liveStage, setLiveStage] = useState<Stage | null>(null);
  const [isCleared, setIsCleared] = useState(false);

  useEffect(() => {
    if (activeAnomaliesCount > 0) {
      setIsCleared(false);
    } else {
      const t = setTimeout(() => {
        setIsCleared(true);
        setDecisions([]);
        setLiveStage(null);
      }, 30000);
      return () => clearTimeout(t);
    }
  }, [activeAnomaliesCount]);

  useEffect(() => {
    // DB polling — for initial page load and completed pipeline state
    const fetchDecisions = async () => {
      if (isCleared) return;
      try {
        const res = await getDecisions();
        setDecisions(res.data || []);
        setLastFetch(new Date().toLocaleTimeString());
      } catch (e) {
        // Keep previous state if offline
      }
    };
    fetchDecisions();
    const id = setInterval(fetchDecisions, 4000);

    // SSE subscription — advances stages in real time during in-flight runs
    const es = new EventSource(`${API_BASE}/sse/pipeline-feed`);
    es.onerror = () => setLiveStage(null);
    es.onmessage = (ev) => {
      try {
        const event = JSON.parse(ev.data);
        switch (event.type) {
          case 'connected':    setLiveStage(null); break;  // reset on reconnect
          case 'anomaly_detected': setLiveStage('detecting'); break;
          case 'diagnosis':    setLiveStage('diagnosing'); break;
          case 'remediation':  setLiveStage('remediating'); break;
          case 'critic':       setLiveStage('critic'); break;
          case 'outcome':
            setLiveStage(event.outcome === 'auto_executed' ? 'done' : 'escalated');
            // Refresh DB state after outcome so the footer stats are accurate
            setTimeout(fetchDecisions, 500);
            // Clear live stage after 10s — return to DB-derived state
            setTimeout(() => setLiveStage(null), 10000);
            break;
          case 'error':        setLiveStage('error'); break;
        }
      } catch (_) {}
    };

    return () => { clearInterval(id); es.close(); };
  }, [isCleared]);

  // Use SSE-driven stage if mid-flight; otherwise derive from last completed DB record
  const current = liveStage ?? deriveStage(decisions);
  const latest  = decisions[0];

  const stages: StageProps[] = [
    { current, name: 'collecting',  label: 'Metrics Collector', subLabel: 'Polling', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg> },
    { current, name: 'detecting',   label: 'Anomaly Detector',  subLabel: 'Isolation Forest', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> },
    { current, name: 'diagnosing',  label: 'Diagnosis Agent',   subLabel: 'Gemini LLM', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg> },
    { current, name: 'remediating', label: 'Remediation Agent', subLabel: 'Gemini LLM', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg> },
    { current, name: 'critic',      label: 'Critic Agent',      subLabel: 'Review & Debate', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg> },
    { current, name: 'policy',      label: 'Policy Engine',     subLabel: 'Risk Evaluation', icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> },
  ];

  const outcomeColor = current === 'done' ? 'var(--color-success)' : current === 'escalated' ? 'var(--color-warning)' : current === 'error' ? 'var(--color-danger)' : 'var(--text-muted)';
  const outcomeText  = current === 'done' ? '✅ Auto-Executed' : current === 'escalated' ? '⚠️ Escalated to Operator' : current === 'error' ? '❌ Pipeline Error — Escalated' : '⏳ Processing…';

  return (
    <div className="card pipeline-card" id="pipeline-card">
      <div className="card-header">
        <h2 className="card-title">Multi-Agent Pipeline</h2>
        <span className="card-subtitle" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Live · updated {lastFetch}
        </span>
      </div>

      <div className="pipeline-visual">
        {stages.map((s, i) => {
          const cls = getStageClass(s.name, current);
          const statusLabel = getStatusLabel(s.name, current, s.subLabel);
          return (
            <React.Fragment key={s.name}>
              <div className={`pipeline-stage ${cls}`} id={`stage-${s.name}`}>
                <div className="stage-icon">{s.icon}</div>
                <span className="stage-label">{s.label}</span>
                <span className={`stage-status${cls === 'active' ? ' processing' : ''}`}>{statusLabel}</span>
              </div>
              {i < stages.length - 1 && (
                <div key={`conn-${i}`} className={`pipeline-connector ${getStageClass(stages[i + 1].name, current) !== '' ? 'completed' : ''}`}></div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {latest && (
        <div style={{ padding: '8px 16px 12px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span>Latest: <code style={{ color: 'var(--accent-primary)' }}>{latest.service || 'payment-service'}</code></span>
          <span>Round: <strong>{latest.round_count || 0}</strong></span>
          <span>Confidence: <strong>{((latest.confidence_score || 0) * 100).toFixed(0)}%</strong></span>
          <span style={{ color: outcomeColor, fontWeight: 600 }}>{outcomeText}</span>
        </div>
      )}
    </div>
  );
}

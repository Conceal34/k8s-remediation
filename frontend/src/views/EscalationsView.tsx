import React, { useEffect, useState, type ReactNode } from 'react';
import { getEscalatedDecisions, submitApproval } from '../api';

const Block = ({ emoji, title, accent, children }: { emoji: string, title: string, accent: string, children: ReactNode }) => (
  <div style={{
    background: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    borderLeft: `3px solid ${accent}`,
    borderRadius: 'var(--radius-sm)',
    padding: '12px 14px',
    marginBottom: '8px',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
      <span style={{ fontSize: '1.1rem' }}>{emoji}</span>
      <strong style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
        {title}
      </strong>
    </div>
    <div style={{ fontSize: '0.79rem', color: 'var(--text-muted)', lineHeight: '1.55' }}>
      {children}
    </div>
  </div>
);

function sevColor(sev: string) {
  if (sev === 'low') return 'var(--color-success)';
  if (sev === 'medium') return 'var(--color-warning)';
  return 'var(--color-danger)';
}

export default function EscalationsView() {
  const [queue, setQueue] = useState<any[]>([]);
  const [activeEscalation, setActiveEscalation] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchEscalations = () => {
    setLoading(true);
    setErrorMsg(null);
    getEscalatedDecisions()
      .then(res => {
        const q = res.data || [];
        setQueue(q);
        if (q.length > 0 && (!activeEscalation || !q.find((d: any) => d.id === activeEscalation.id))) {
          setActiveEscalation(q[0]);
        } else if (q.length === 0) {
          setActiveEscalation(null);
        }
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        setErrorMsg("Failed to load escalations. Please check your connection.");
        setQueue([]);
        setActiveEscalation(null);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchEscalations();
  }, []);

  const handleAction = async (action: string, edited_action?: string) => {
    if (!activeEscalation?.id) return;
    try {
      await submitApproval(activeEscalation.id, { 
        operator: "admin", 
        action_taken: action,
        edited_action: edited_action
      });
      // Remove from queue locally
      const newQueue = queue.filter(q => q.id !== activeEscalation.id);
      setQueue(newQueue);
      if (newQueue.length > 0) {
        setActiveEscalation(newQueue[0]);
      } else {
        setActiveEscalation(null);
      }
    } catch(e: any) {
      console.error(e);
      alert(`Failed to submit approval: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleEdit = () => {
    const defaultAction = activeEscalation?.final_action || "restart";
    const edited = prompt("Enter the modified action (e.g., restart, scale_up, rollback):", defaultAction);
    if (edited && edited !== "") {
      handleAction("edit", edited);
    }
  };

  return (
    <section className="view active" id="view-escalations">
      <div className="escalation-detail" id="escalation-detail" style={{ display: 'flex', gap: '20px' }}>
        
        {/* Left Side: Queue Panel */}
        <div className="escalation-queue-panel" style={{ flex: '0 0 300px' }}>
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Pending Escalations</h2>
              <span className="badge badge-error">{queue.length}</span>
            </div>
            <div className="escalation-queue" id="escalation-queue">
              {loading && <div style={{ padding: '16px', color: 'var(--text-muted)' }}>Loading...</div>}
              {errorMsg && <div style={{ padding: '16px', color: 'var(--color-danger)' }}>{errorMsg}</div>}
              {!loading && !errorMsg && queue.length === 0 && (
                <div style={{ padding: '16px', color: 'var(--text-muted)' }}>No pending escalations. All clear!</div>
              )}
              {queue.map((item, idx) => {
                const service = item.service || item.anomaly?.service || item.anomaly?.metric_sample?.service || "unknown";
                const isSelected = activeEscalation?.id === item.id;
                return (
                  <div 
                    key={item.id || idx} 
                    className={`queue-item ${isSelected ? 'active' : ''}`}
                    onClick={() => setActiveEscalation(item)}
                    style={{ cursor: 'pointer', padding: '12px', borderBottom: '1px solid var(--border-color)', background: isSelected ? 'var(--bg-tertiary)' : 'transparent' }}
                  >
                    <div className="item-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span className="item-service" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-primary)' }}>
                        {service}
                      </span>
                      <span className="item-time" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                        {item.created_at ? new Date(item.created_at).toLocaleTimeString() : ''}
                      </span>
                    </div>
                    <div className="item-title" style={{ fontSize: '0.85rem' }}>
                      Anomaly #{item.anomaly?.id || item.anomaly_id}
                    </div>
                    <div className="item-meta" style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                      <span className={`risk-badge ${item.risk_tier || 'high'}`}>{item.risk_tier || 'high'} Risk</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Side: Active Escalation Detail */}
        <div className="escalation-content-panel" style={{ flex: '1', minWidth: 0 }}>
          {!activeEscalation && !loading ? (
            <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <h3>No Escalations Selected</h3>
              <p>The queue is currently empty.</p>
            </div>
          ) : activeEscalation ? (
            <div className="card">
              <div className="card-header" style={{ paddingBottom: '16px' }}>
                <h2 className="card-title">Escalation Review</h2>
                <div className="escalation-meta" style={{ display: 'flex', gap: '10px' }}>
                  <span className={`risk-badge ${activeEscalation.risk_tier || 'high'}`}>{activeEscalation.risk_tier || 'high'} Risk</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-primary)', padding: '2px 8px', background: 'var(--bg-tertiary)', borderRadius: '4px' }}>
                    {activeEscalation.service || activeEscalation.anomaly?.service || "unknown"}
                  </span>
                </div>
              </div>

              <div style={{ padding: '0 20px 20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {/* Detection */}
                {activeEscalation.anomaly && typeof activeEscalation.anomaly === 'object' && (
                  <Block emoji="🌲" title="Isolation Forest — Detection" accent={sevColor(activeEscalation.anomaly.severity)}>
                    Score: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>{activeEscalation.anomaly.score?.toFixed(3) || '0.000'}</span>
                    {' '}· Detected At: {activeEscalation.anomaly.detected_at ? new Date(activeEscalation.anomaly.detected_at).toLocaleTimeString() : '—'}
                  </Block>
                )}

                {/* Diagnosis */}
                {activeEscalation.diagnosis_text && (
                  <Block emoji="🧠" title="Diagnosis Agent — Gemini" accent="var(--accent-primary)">
                    {activeEscalation.diagnosis_text}
                  </Block>
                )}

                {/* Debate Trail */}
                {activeEscalation.remediation_proposals && activeEscalation.remediation_proposals.map((prop: any, idx: number) => {
                  const verdict = (activeEscalation.critic_verdicts || []).find((v: any) => v.round === prop.round);
                  return (
                    <React.Fragment key={idx}>
                      <Block emoji="🛠️" title={`Remediation Agent — Round ${prop.round}`} accent="var(--color-info)">
                        Action: <strong style={{ color: 'var(--text-primary)' }}>{prop.action}</strong>
                        <br />
                        <span style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)' }}>{prop.justification}</span>
                      </Block>
                      {verdict && (
                        <Block emoji="⚖️" title={`Critic Agent — Round ${verdict.round}`}
                          accent={verdict.verdict === 'APPROVE' ? 'var(--color-success)' : 'var(--color-warning)'}>
                          Verdict:{' '}
                          <strong style={{ color: verdict.verdict === 'APPROVE' ? 'var(--color-success)' : 'var(--color-warning)' }}>
                            {verdict.verdict}
                          </strong>
                          {verdict.confidence !== undefined && (
                            <>
                              {' '}· Confidence: <strong style={{ color: 'var(--color-success)' }}>{Math.round(verdict.confidence * 100)}%</strong>
                            </>
                          )}
                          <br />
                          <span style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)' }}>{verdict.reason}</span>
                        </Block>
                      )}
                    </React.Fragment>
                  );
                })}

                {/* Policy Engine */}
                <Block emoji="🛡️" title="Policy Engine — Escalated" accent="var(--color-warning)">
                  The Policy Engine escalated this decision because automatic execution criteria were not met.
                  <br />
                  Proposed Action: <strong style={{ color: 'var(--text-primary)' }}>{activeEscalation.final_action}</strong>
                  {' '}· System Confidence: {Math.round((activeEscalation.confidence_score || 0) * 100)}%
                </Block>

                {/* Operator Actions */}
                <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
                  <h3 style={{ fontSize: '0.9rem', marginBottom: '12px' }}>Operator Override</h3>
                  <div className="action-buttons" style={{ display: 'flex', gap: '12px' }}>
                    <button className="btn btn-approve" onClick={() => handleAction('approve')} style={{ flex: 1, padding: '10px', background: 'var(--color-success)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>
                      ✓ Approve
                    </button>
                    <button className="btn btn-edit" onClick={handleEdit} style={{ flex: 1, padding: '10px', background: 'var(--color-info)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>
                      ✎ Edit Action
                    </button>
                    <button className="btn btn-reject" onClick={() => handleAction('reject')} style={{ flex: 1, padding: '10px', background: 'var(--color-danger)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>
                      ✕ Reject
                    </button>
                  </div>
                </div>

              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

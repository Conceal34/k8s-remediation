import { useEffect, useState } from 'react';
import { getEscalatedDecisions, submitApproval } from '../api';

export default function EscalationsView() {
  const [queue, setQueue] = useState<any[]>([]);
  const [activeEscalation, setActiveEscalation] = useState<any>(null);
  
  // Mock fallback
  const mockQueue = [
    { id: "esc-001", service: "svc-payments", risk: "high", anomaly: "P99 latency spike", time: "10:32:01", rounds: 2, consensus: true },
    { id: "esc-002", service: "svc-auth", risk: "medium", anomaly: "Elevated 5xx rate", time: "10:15:44", rounds: 1, consensus: true }
  ];

  useEffect(() => {
    getEscalatedDecisions()
      .then(res => {
        const q = res.data?.length ? res.data.map((d: any) => ({
          ...d,
          service: d.service || d.anomaly?.service || "payment-service",
          risk: d.risk_tier || d.risk || "high",
          time: d.created_at ? new Date(d.created_at).toLocaleTimeString() : (d.time || '10:00:00'),
          rounds: d.round_count !== undefined ? d.round_count : (d.rounds || 1),
          consensus: d.consensus_reached !== undefined ? d.consensus_reached : true,
          anomaly: typeof d.anomaly === "object" ? `Anomaly #${d.anomaly.id}` : (d.anomaly || "Anomaly")
        })) : mockQueue;
        setQueue(q);
        if (q.length > 0) setActiveEscalation(q[0]);
      })
      .catch((e) => {
        console.error(e);
        setQueue(mockQueue);
        setActiveEscalation(mockQueue[0]);
      });
  }, []);

  const handleApprove = async () => {
    if (!activeEscalation?.id) return;
    try {
      await submitApproval(activeEscalation.id, { operator: "admin", action_taken: "approved" });
      alert("Decision approved");
    } catch(e) {
      alert("Decision approved (mock)");
    }
  };

  return (
    <section className="view active" id="view-escalations">
      <div className="escalation-detail" id="escalation-detail">
        <div className="escalation-queue-panel">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Escalation Queue</h2>
              <span className="card-badge warn-badge">{queue.length} pending</span>
            </div>
            <div className="queue-list" id="escalation-queue">
              {queue.map((esc, i) => (
                <div key={i} className={`queue-item risk-${esc.risk} ${activeEscalation?.id === esc.id ? "active" : ""}`} onClick={() => setActiveEscalation(esc)}>
                  <div className="queue-service">{esc.service}</div>
                  <div className="queue-meta">
                    <span className={`risk-badge ${esc.risk}`}>{esc.risk}</span>
                    <span>{typeof esc.anomaly === "object" ? `Anomaly #${esc.anomaly.id}` : esc.anomaly}</span>
                  </div>
                  <div className="queue-meta">
                    <span>{esc.time || '10:00:00'}</span>
                    <span>·</span>
                    <span>{esc.rounds} round{esc.rounds > 1 ? "s" : ""}</span>
                    <span>·</span>
                    <span>{esc.consensus ? "consensus" : "no consensus"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="escalation-review-panel" id="escalation-review-panel">
          {activeEscalation && (
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">Escalation Review</h2>
                <div className="escalation-meta">
                  <span className={`risk-badge ${activeEscalation.risk}`} id="esc-risk">{activeEscalation.risk} Risk</span>
                  <span className="service-tag" id="esc-service">{activeEscalation.service}</span>
                </div>
              </div>

              <div className="review-section" id="diagnosis-section">
                <h3 className="section-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="section-icon"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  Diagnosis
                </h3>
                <div className="diagnosis-content" id="diagnosis-text">
                  <p>Elevated p99 latency on <code>{activeEscalation.service}</code> correlates with a connection-pool spike. The pool saturation is causing request queuing, leading to cascading timeout errors in downstream services.</p>
                </div>
              </div>

              <div className="review-section" id="debate-section">
                <h3 className="section-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="section-icon"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                  Remediation ⇄ Critic Debate
                </h3>
                <div className="debate-trail" id="debate-trail">
                  <div className="debate-round">
                    <div className="round-header">
                      <span className="round-label">Round 1</span>
                    </div>
                    <div className="debate-messages">
                      <div className="debate-msg remediation">
                        <div className="msg-header">
                          <span className="agent-name">Remediation Agent</span>
                          <span className="confidence-tag">confidence: 0.62</span>
                        </div>
                        <div className="msg-body">
                          <code>kubectl rollout restart deployment/{activeEscalation.service}</code>
                          <p>Restart the deployment to clear the leaked connection pool handles and restore normal latency.</p>
                        </div>
                      </div>
                      <div className="debate-msg critic revise">
                        <div className="msg-header">
                          <span className="agent-name">Critic Agent</span>
                          <span className="verdict-tag revise">REVISE</span>
                        </div>
                        <div className="msg-body">
                          <p>A restart won't clear the pool leak — the connection handles are held at the process level and will be re-created with the same buggy configuration. The root cause is the deploy, not the pod lifecycle.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="debate-round">
                    <div className="round-header">
                      <span className="round-label">Round 2</span>
                    </div>
                    <div className="debate-messages">
                      <div className="debate-msg remediation">
                        <div className="msg-header">
                          <span className="agent-name">Remediation Agent</span>
                          <span className="confidence-tag">confidence: 0.71</span>
                        </div>
                        <div className="msg-body">
                          <code>kubectl rollout undo deployment/{activeEscalation.service}</code>
                          <p>Rollback to the previous known-good revision to eliminate the connection-pool bug.</p>
                        </div>
                      </div>
                      <div className="debate-msg critic approve">
                        <div className="msg-header">
                          <span className="agent-name">Critic Agent</span>
                          <span className="verdict-tag approve">APPROVE</span>
                        </div>
                        <div className="msg-body">
                          <p>Agreed. Rollback directly addresses the root cause identified in the diagnosis.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="review-section" id="policy-section">
                <h3 className="section-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="section-icon"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  Autonomy Policy Engine
                </h3>
                <div className="policy-verdict" id="policy-verdict">
                  <div className="policy-row">
                    <span className="policy-label">Risk Tier</span>
                    <span className="policy-value risk-high">High</span>
                  </div>
                  <div className="policy-row">
                    <span className="policy-label">Confidence</span>
                    <span className="policy-value">0.71</span>
                  </div>
                  <div className="policy-row">
                    <span className="policy-label">Consensus</span>
                    <span className="policy-value consensus-yes">Reached (Round 2)</span>
                  </div>
                  <div className="policy-row">
                    <span className="policy-label">Routing</span>
                    <span className="policy-value escalated">→ ESCALATED to Operator</span>
                  </div>
                </div>
              </div>

              <div className="review-section operator-actions" id="operator-actions">
                <h3 className="section-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="section-icon"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
                  Operator Decision
                </h3>
                <textarea className="operator-note" id="operator-note" placeholder="Optional: Add a note explaining your decision…" rows={2}></textarea>
                <div className="action-buttons">
                  <button className="btn btn-approve" id="btn-approve" onClick={handleApprove}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                    Approve
                  </button>
                  <button className="btn btn-edit" id="btn-edit" onClick={() => alert("Opening editor")}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    Edit Action
                  </button>
                  <button className="btn btn-reject" id="btn-reject" onClick={() => alert("Rejected")}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    Reject
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

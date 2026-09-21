import React, { useState, type ReactNode } from 'react';

// Helper component identical to the one in AgentFeed
const Block = ({ emoji, title, accent, children }: { emoji: string, title: string, accent: string, children: ReactNode }) => (
  <div style={{
    background: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    borderLeft: `3px solid ${accent}`,
    borderRadius: 'var(--radius-sm)',
    padding: '12px 14px',
    animation: 'feedIn 0.3s ease',
    marginBottom: '8px',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
      <span style={{ fontSize: '1.1rem' }}>{emoji}</span>
      <strong style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
        {title}
      </strong>
    </div>
    <div style={{ fontSize: '0.79rem', color: 'var(--text-muted)', lineHeight: '1.55', wordBreak: 'break-word', whiteSpace: 'pre-wrap', overflowWrap: 'break-word' }}>
      {children}
    </div>
  </div>
);

function sevColor(sev: string) {
  if (sev === 'low') return 'var(--color-success)';
  if (sev === 'medium') return 'var(--color-warning)';
  return 'var(--color-danger)';
}

export default function DecisionTable({ decisions }: { decisions: any[] }) {
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);

  const toggleRow = (id: number) => {
    setExpandedRowId(expandedRowId === id ? null : id);
  };

  return (
    <>
      <table className="data-table" id="decision-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Service</th>
            <th>Anomaly</th>
            <th>Risk</th>
            <th>Confidence</th>
            <th>Rounds</th>
            <th>Outcome</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {decisions.length === 0 ? (
            <tr>
              <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                No recent decisions recorded.
              </td>
            </tr>
          ) : decisions.map((d: any, i: number) => {
            
            const service = d.service || d.anomaly?.service || d.anomaly?.metric_sample?.service || "unknown-service";
            const anomalyIdStr = typeof d.anomaly === "object" ? `Anomaly #${d.anomaly.id}` : (d.anomaly || d.anomaly_type || "Anomaly");
            const risk = d.risk_tier || d.risk || "low";
            
            let confidence = 0;
            const rawConf = d.confidence_score !== undefined ? d.confidence_score : d.confidence;
            if (typeof rawConf === 'number' && !isNaN(rawConf)) confidence = rawConf;
            
            let rounds = 0;
            const rawRounds = d.round_count !== undefined ? d.round_count : d.rounds;
            if (typeof rawRounds === 'number' && !isNaN(rawRounds)) rounds = rawRounds;
            
            const outcome = String(d.autonomy_outcome || d.outcome || "unknown");
            const action = d.final_action || d.action || "none";
            const time = d.created_at ? new Date(d.created_at).toLocaleTimeString() : (d.time || new Date().toLocaleTimeString());
            const isExpanded = expandedRowId === d.id;

            return (
              <React.Fragment key={d.id || i}>
                <tr 
                  onClick={() => toggleRow(d.id)} 
                  style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-tertiary)' : 'transparent' }}
                  title="Click to view full agent intelligence feed"
                >
                  <td className="cell-mono">{time}</td>
                  <td><code style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{service}</code></td>
                  <td>{anomalyIdStr}</td>
                  <td><span className={`risk-badge ${risk}`}>{risk}</span></td>
                  <td className="cell-mono">{confidence.toFixed(2)}</td>
                  <td className="cell-mono">{rounds}</td>
                  <td>
                    <span className={`outcome-badge ${outcome}`}>
                      {outcome === "auto" ? "Auto-Executed" : (outcome === "auto_executed" ? "Auto-Executed" : outcome.charAt(0).toUpperCase() + outcome.slice(1))}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    {action} {isExpanded ? '▼' : '▶'}
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={8} style={{ padding: '16px 24px', background: 'var(--bg-main)', borderBottom: '1px solid var(--border-color)' }}>
                      <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        
                        {/* Detection Block */}
                        {d.anomaly && typeof d.anomaly === 'object' && (
                          <Block emoji="🌲" title="Isolation Forest — Detection" accent={sevColor(d.anomaly.severity)}>
                            Anomaly on <code style={{ color: 'var(--accent-primary)' }}>{service}</code>
                            {' '}· Severity{' '}
                            <strong style={{ color: sevColor(d.anomaly.severity) }}>{d.anomaly.severity?.toUpperCase()}</strong>
                            {' '}· Score{' '}
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>{d.anomaly.score?.toFixed(3) || '0.000'}</span>
                            <br />
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                              {d.anomaly.detected_at ? new Date(d.anomaly.detected_at).toLocaleTimeString() : '—'}
                            </span>
                          </Block>
                        )}

                        {/* Diagnosis Block */}
                        {d.diagnosis_text && (
                          <Block emoji="🧠" title="Diagnosis Agent — Gemini" accent="var(--accent-primary)">
                            {d.diagnosis_text}
                          </Block>
                        )}

                        {/* Remediation & Critic Rounds */}
                        {d.remediation_proposals && d.remediation_proposals.map((prop: any, idx: number) => {
                          // Find corresponding critic verdict if any
                          const verdict = (d.critic_verdicts || []).find((v: any) => v.round === prop.round);
                          
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

                        {/* Outcome Block */}
                        <div style={{
                          textAlign: 'center', padding: '10px', marginTop: '4px',
                          borderRadius: 'var(--radius-sm)',
                          background: outcome === 'auto_executed' || outcome === 'auto' ? 'var(--color-success-dim)' : 'rgba(255,170,0,0.1)',
                          color: outcome === 'auto_executed' || outcome === 'auto' ? 'var(--color-success)' : 'var(--color-warning)',
                          fontWeight: 600, fontSize: '0.82rem',
                          animation: 'feedIn 0.4s ease',
                        }}>
                          {outcome === 'auto_executed' || outcome === 'auto' ? '✅ Auto-Executed' : '⚠️ Escalated to Operator'}
                          <span style={{ fontWeight: 400, marginLeft: '8px', color: 'inherit', opacity: 0.75 }}>
                            · {action}
                          </span>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
      <style>{`
        @keyframes feedIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  );
}

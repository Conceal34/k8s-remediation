export default function DecisionTable({ decisions }: { decisions: any[] }) {
  const data = (decisions || []).map((d: any) => {
    const service = d.service || d.anomaly?.service || d.anomaly?.metric_sample?.service || "payment-service";
    const anomaly = typeof d.anomaly === "object" ? `Anomaly #${d.anomaly.id}` : (d.anomaly || d.anomaly_type || "Anomaly");
    const risk = d.risk_tier || d.risk || "low";
    
    let confidence = 0;
    const rawConf = d.confidence_score !== undefined ? d.confidence_score : d.confidence;
    if (typeof rawConf === 'number' && !isNaN(rawConf)) {
      confidence = rawConf;
    }
    
    let rounds = 0;
    const rawRounds = d.round_count !== undefined ? d.round_count : d.rounds;
    if (typeof rawRounds === 'number' && !isNaN(rawRounds)) {
      rounds = rawRounds;
    }
    
    const outcome = String(d.autonomy_outcome || d.outcome || "unknown");
    const action = d.final_action || d.action || "none";
    const time = d.created_at ? new Date(d.created_at).toLocaleTimeString() : (d.time || new Date().toLocaleTimeString());

    return {
      time,
      service,
      anomaly,
      risk,
      confidence,
      rounds,
      outcome,
      action
    };
  });

  return (
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
        {data.length === 0 ? (
          <tr>
            <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
              No recent decisions recorded.
            </td>
          </tr>
        ) : data.map((d, i) => (
          <tr key={i}>
            <td className="cell-mono">{d.time}</td>
            <td><code style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{d.service}</code></td>
            <td>{d.anomaly}</td>
            <td><span className={`risk-badge ${d.risk}`}>{d.risk}</span></td>
            <td className="cell-mono">{d.confidence.toFixed(2)}</td>
            <td className="cell-mono">{d.rounds}/2</td>
            <td><span className={`outcome-badge ${d.outcome}`}>{d.outcome === "auto" ? "Auto-Executed" : (d.outcome === "auto_executed" ? "Auto-Executed" : d.outcome.charAt(0).toUpperCase() + d.outcome.slice(1))}</span></td>
            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{d.action}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

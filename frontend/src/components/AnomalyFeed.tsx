export default function AnomalyFeed({ anomalies }: { anomalies: any[] }) {
  const feed = anomalies || [];

  return (
    <div className="card anomaly-feed-card" id="anomaly-feed-card">
      <div className="card-header">
        <h2 className="card-title">Anomaly Feed</h2>
        <span className="card-badge live-badge">
          <span className="pulse-dot small"></span> Live
        </span>
      </div>
      <div className="anomaly-feed" id="anomaly-feed">
        {feed.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No active anomalies detected. System is operating normally.
          </div>
        ) : feed.map((a, i) => {
          const serviceName = a.service || (a.anomaly?.service) || "payment-service";
          const metricLabel = (a.metric_type || "Metric").toUpperCase();
          const scoreText = typeof a.score === 'number' ? a.score.toFixed(2) : (a.score || "0.85");
          const descriptionText = a.desc || a.description || `${metricLabel} deviation detected by Isolation Forest (score: ${scoreText})`;
          const timeText = a.time || (a.detected_at ? new Date(a.detected_at).toLocaleTimeString() : new Date().toLocaleTimeString());

          return (
            <div key={i} className={`anomaly-item severity-${a.severity || 'medium'}`}>
              <div className="anomaly-info">
                <div className="anomaly-service">{serviceName}</div>
                <div className="anomaly-desc">{descriptionText}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                <span className={`anomaly-severity ${a.severity || 'medium'}`}>{a.severity || 'medium'}</span>
                <span className="anomaly-time">{timeText}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

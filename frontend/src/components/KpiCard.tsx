
export default function KpiCard({ id, title, value, trend, trendClass }: any) {
  let chipClass = '';
  let chipLabel = '';

  if (id === 'kpi-anomalies') {
    chipClass = 'chip-red';
    chipLabel = 'Anomalies';
  } else if (id === 'kpi-escalated') {
    chipClass = 'chip-amber';
    chipLabel = 'Escalated';
  } else if (id === 'kpi-auto') {
    chipClass = 'chip-green';
    chipLabel = 'Auto';
  } else {
    chipClass = 'chip-violet';
    chipLabel = 'Rounds';
  }

  return (
    <div className="kpi-card" id={id}>
      <div className="kpi-top-row">
        <span className={`kpi-chip ${chipClass}`}>{chipLabel}</span>
      </div>
      <div className="kpi-content">
        <span className="kpi-value">{value}</span>
        <span className="kpi-label">{title}</span>
      </div>
      <span className={`kpi-trend ${trendClass}`}>{trend}</span>
    </div>
  );
}

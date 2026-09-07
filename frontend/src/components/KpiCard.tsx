

export default function KpiCard({ id, title, value, trend, trendClass }: any) {
  let icon = null;
  let iconClass = "";
  
  if (id === 'kpi-anomalies') {
    iconClass = "anomaly-icon";
    icon = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>;
  } else if (id === 'kpi-escalated') {
    iconClass = "escalation-icon";
    icon = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>;
  } else if (id === 'kpi-auto') {
    iconClass = "auto-icon";
    icon = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>;
  } else {
    iconClass = "rounds-icon";
    icon = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/></svg>;
  }

  return (
    <div className="kpi-card" id={id}>
      <div className={`kpi-icon ${iconClass}`}>
        {icon}
      </div>
      <div className="kpi-content">
        <span className="kpi-value">{value}</span>
        <span className="kpi-label">{title}</span>
      </div>
      <span className={`kpi-trend ${trendClass}`}>{trend}</span>
    </div>
  );
}

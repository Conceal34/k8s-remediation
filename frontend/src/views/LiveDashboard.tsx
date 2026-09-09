import { useEffect, useState } from 'react';
import { getActiveAnomalies } from '../api';
import KpiCard from '../components/KpiCard';
import AnomalyFeed from '../components/AnomalyFeed';
import MetricsChart from '../components/MetricsChart';
import PipelineVisual from '../components/PipelineVisual';
import AgentFeed from '../components/AgentFeed';
import DecisionTable from '../components/DecisionTable';
import { getDecisions } from '../api';

export default function LiveDashboard({ onViewChange }: { onViewChange?: (v: string) => void }) {
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);

  useEffect(() => {
    // Fetch data initially and periodically
    const fetchData = async () => {
      try {
        const anomaliesRes = await getActiveAnomalies();
        setAnomalies(anomaliesRes.data || []);
      } catch (e) {
        console.error("Failed to fetch anomalies", e);
      }
      
      try {
        const decisionsRes = await getDecisions();
        setDecisions(decisionsRes.data || []);
      } catch (e) {
        console.error("Failed to fetch decisions", e);
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const escalatedCount = decisions.filter((d: any) => d.autonomy_outcome === 'escalated' && !d.approval).length;
  const autoCount = decisions.filter((d: any) => d.autonomy_outcome === 'auto_executed').length;
  const avgRounds = decisions.length > 0 ? (decisions.reduce((acc: number, d: any) => acc + (d.round_count || 1), 0) / decisions.length).toFixed(1) : "0";

  return (
    <section className="view active" id="view-live">
      <div className="kpi-row">
        <KpiCard id="kpi-anomalies" title="Active Anomalies" value={anomalies.length} trend={anomalies.length > 0 ? "attention needed" : "stable"} trendClass={anomalies.length > 0 ? "up" : "neutral"} />
        <KpiCard id="kpi-escalated" title="Pending Escalations" value={escalatedCount} trend="awaiting review" trendClass={escalatedCount > 0 ? "up" : "neutral"} />
        <KpiCard id="kpi-auto" title="Auto-Resolved" value={autoCount} trend="system healed" trendClass="down" />
        <KpiCard id="kpi-avg-rounds" title="Avg Debate Rounds" value={avgRounds} trend="efficiency" trendClass="down" />
      </div>

      <div className="charts-row">
        <MetricsChart />
        <AnomalyFeed anomalies={anomalies} />
      </div>

      <div className="pipeline-row">
        <PipelineVisual activeAnomaliesCount={anomalies.length} />
        <AgentFeed activeAnomaliesCount={anomalies.length} />
      </div>

      <div className="card table-card" id="history-table-card">
        <div className="card-header">
          <h2 className="card-title">Recent Decisions</h2>
          <button className="btn-ghost" id="view-all-history" onClick={() => onViewChange && onViewChange('history')}>View all →</button>
        </div>
        <div className="table-wrapper">
          <DecisionTable decisions={decisions.slice(0, 5)} />
        </div>
      </div>
    </section>
  );
}

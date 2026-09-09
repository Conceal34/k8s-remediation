import { useEffect, useState } from 'react';
import DecisionTable from '../components/DecisionTable';
import { getDecisions } from '../api';

export default function HistoryView() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [riskFilter, setRiskFilter] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    getDecisions({ risk: riskFilter, outcome: outcomeFilter })
      .then(res => {
        setDecisions(res.data || []);
        setErrorMsg(null);
      })
      .catch(e => {
        console.error(e);
        setErrorMsg("Failed to load decision history.");
      });
  }, [riskFilter, outcomeFilter]);

  return (
    <section className="view active" id="view-history">
      <div className="card table-card">
        <div className="card-header">
          <h2 className="card-title">Full Decision History</h2>
          <div className="history-filters">
            <select className="filter-select" id="filter-risk" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
              <option value="">All Risks</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select className="filter-select" id="filter-outcome" value={outcomeFilter} onChange={e => setOutcomeFilter(e.target.value)}>
              <option value="">All Outcomes</option>
              <option value="auto_executed">Auto-Executed</option>
              <option value="escalated">Escalated</option>
            </select>
          </div>
        </div>
        <div className="table-wrapper">
          {errorMsg ? (
            <div style={{ padding: '20px', color: 'var(--color-danger)', textAlign: 'center' }}>
              {errorMsg}
            </div>
          ) : (
            <DecisionTable decisions={decisions} />
          )}
        </div>
      </div>
    </section>
  );
}

import { useEffect, useState } from 'react';
import DecisionTable from '../components/DecisionTable';
import { getDecisions } from '../api';

export default function HistoryView() {
  const [decisions, setDecisions] = useState<any[]>([]);

  useEffect(() => {
    getDecisions().then(res => setDecisions(res.data || [])).catch(console.error);
  }, []);

  return (
    <section className="view active" id="view-history">
      <div className="card table-card">
        <div className="card-header">
          <h2 className="card-title">Full Decision History</h2>
          <div className="history-filters">
            <select className="filter-select" id="filter-risk">
              <option value="">All Risks</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select className="filter-select" id="filter-outcome">
              <option value="">All Outcomes</option>
              <option value="auto">Auto-Executed</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>
        <div className="table-wrapper">
          <DecisionTable decisions={decisions} />
        </div>
      </div>
    </section>
  );
}

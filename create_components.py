import os

frontend_src = "agentic-cloudops/frontend/src"
components_dir = os.path.join(frontend_src, "components")
views_dir = os.path.join(frontend_src, "views")

os.makedirs(components_dir, exist_ok=True)
os.makedirs(views_dir, exist_ok=True)

app_tsx = """import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import LiveDashboard from './views/LiveDashboard';
import EscalationsView from './views/EscalationsView';
import HistoryView from './views/HistoryView';
import SettingsView from './views/SettingsView';
import './index.css';

export default function App() {
  const [currentView, setCurrentView] = useState('live');

  return (
    <>
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <main className="main-content">
        <TopBar currentView={currentView} />
        <div style={{ display: currentView === 'live' ? 'block' : 'none' }}>
          <LiveDashboard />
        </div>
        <div style={{ display: currentView === 'escalations' ? 'block' : 'none' }}>
          <EscalationsView />
        </div>
        <div style={{ display: currentView === 'history' ? 'block' : 'none' }}>
          <HistoryView />
        </div>
        <div style={{ display: currentView === 'settings' ? 'block' : 'none' }}>
          <SettingsView />
        </div>
      </main>
    </>
  );
}
"""

sidebar_tsx = """import React from 'react';

export default function Sidebar({ currentView, onViewChange }: { currentView: string, onViewChange: (view: string) => void }) {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <span className="brand-text">CloudOps</span>
      </div>
      <nav className="sidebar-nav">
        <a href="#" className={`nav-item ${currentView === 'live' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); onViewChange('live'); }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <span>Live</span>
        </a>
        <a href="#" className={`nav-item ${currentView === 'escalations' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); onViewChange('escalations'); }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <span>Escalations</span>
          <span className="nav-badge" id="escalation-badge">2</span>
        </a>
        <a href="#" className={`nav-item ${currentView === 'history' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); onViewChange('history'); }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span>History</span>
        </a>
        <a href="#" className={`nav-item ${currentView === 'settings' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); onViewChange('settings'); }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          <span>Settings</span>
        </a>
      </nav>
      <div className="sidebar-footer">
        <div className="cluster-status">
          <span className="status-dot online"></span>
          <span className="status-text">minikube</span>
        </div>
      </div>
    </aside>
  );
}
"""

topbar_tsx = """import React, { useEffect, useState } from 'react';

const titles: Record<string, string[]> = {
  live: ["Live Dashboard", "Real-time cluster health & anomaly detection"],
  escalations: ["Escalation Queue", "Review pending decisions requiring operator approval"],
  history: ["Decision History", "Full audit trail of all anomaly responses"],
  settings: ["Configuration", "Anomaly thresholds, policy rules & remediation whitelist"],
};

export default function TopBar({ currentView }: { currentView: string }) {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }));
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  const [title, subtitle] = titles[currentView] || ["", ""];

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <h1 className="page-title">{title}</h1>
        <span className="page-subtitle">{subtitle}</span>
      </div>
      <div className="top-bar-right">
        <div className="system-health">
          <span className="health-label">System Health</span>
          <span className="health-indicator healthy">
            <span className="pulse-dot"></span>
            Operational
          </span>
        </div>
        <div className="timestamp">{timeStr}</div>
      </div>
    </header>
  );
}
"""

livedashboard_tsx = """import React, { useEffect, useRef, useState } from 'react';
import { getLiveMetrics, getActiveAnomalies } from '../api';
import KpiCard from '../components/KpiCard';
import AnomalyFeed from '../components/AnomalyFeed';
import MetricsChart from '../components/MetricsChart';
import PipelineVisual from '../components/PipelineVisual';
import DecisionTable from '../components/DecisionTable';
import { getDecisions } from '../api';

export default function LiveDashboard() {
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

  return (
    <section className="view active" id="view-live">
      <div className="kpi-row">
        <KpiCard id="kpi-anomalies" title="Active Anomalies" value={anomalies.length} trend="↑ 1 in 5m" trendClass="up" />
        <KpiCard id="kpi-escalated" title="Pending Escalations" value={2} trend="awaiting review" trendClass="neutral" />
        <KpiCard id="kpi-auto" title="Auto-Resolved (24h)" value={7} trend="↓ 2 vs yesterday" trendClass="down" />
        <KpiCard id="kpi-avg-rounds" title="Avg Debate Rounds" value={1.3} trend="↓ 0.2" trendClass="down" />
      </div>

      <div className="charts-row">
        <MetricsChart />
        <AnomalyFeed anomalies={anomalies} />
      </div>

      <PipelineVisual />

      <div className="card table-card" id="history-table-card">
        <div className="card-header">
          <h2 className="card-title">Recent Decisions</h2>
          <button className="btn-ghost" id="view-all-history">View all →</button>
        </div>
        <div className="table-wrapper">
          <DecisionTable decisions={decisions.slice(0, 5)} />
        </div>
      </div>
    </section>
  );
}
"""

kpicard_tsx = """import React from 'react';

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
"""

metrics_chart_tsx = """import React, { useEffect, useRef } from 'react';

export default function MetricsChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    function drawMetricsChart() {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (!rect) return;

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      const W = rect.width;
      const H = rect.height;
      const pad = { top: 20, right: 20, bottom: 40, left: 50 };
      const chartW = W - pad.left - pad.right;
      const chartH = H - pad.top - pad.bottom;

      const timeLabels = [];
      const now = new Date();
      for (let i = 11; i >= 0; i--) {
        const t = new Date(now.getTime() - i * 15000);
        timeLabels.push(
          t.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        );
      }

      function genData(base: number, variance: number, spike: any) {
        const d = [];
        for (let i = 0; i < 12; i++) {
          let v = base + (Math.random() - 0.5) * variance;
          if (spike && i === spike.at) v += spike.amount;
          d.push(Math.max(0, Math.min(100, v)));
        }
        return d;
      }

      const cpuData = genData(55, 15, { at: 8, amount: 25 });
      const memData = genData(42, 8, null);
      const errData = genData(5, 6, { at: 8, amount: 18 });

      ctx.clearRect(0, 0, W, H);

      ctx.strokeStyle = "rgba(255,255,255,0.04)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {
        const y = pad.top + (chartH / 5) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(W - pad.right, y);
        ctx.stroke();
      }

      ctx.fillStyle = "#5a6371";
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = "right";
      for (let i = 0; i <= 5; i++) {
        const val = 100 - i * 20;
        const y = pad.top + (chartH / 5) * i;
        ctx.fillText(val + "%", pad.left - 8, y + 4);
      }

      ctx.textAlign = "center";
      const step = chartW / (timeLabels.length - 1);
      for (let i = 0; i < timeLabels.length; i += 2) {
        const x = pad.left + step * i;
        ctx.fillText(timeLabels[i], x, H - pad.bottom + 20);
      }

      function drawLine(data: number[], color: string, alpha: number) {
        if (!ctx) return;
        const points = data.map((v, i) => ({
          x: pad.left + (chartW / (data.length - 1)) * i,
          y: pad.top + chartH - (v / 100) * chartH,
        }));

        const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
        gradient.addColorStop(0, color.replace(")", `,${alpha})`).replace("rgb", "rgba"));
        gradient.addColorStop(1, color.replace(")", ",0)").replace("rgb", "rgba"));

        ctx.beginPath();
        ctx.moveTo(points[0].x, pad.top + chartH);
        points.forEach((p) => ctx.lineTo(p.x, p.y));
        ctx.lineTo(points[points.length - 1].x, pad.top + chartH);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) {
          const cpx = (points[i - 1].x + points[i].x) / 2;
          ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, cpx, (points[i - 1].y + points[i].y) / 2);
        }
        ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        points.forEach((p) => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
          ctx.fillStyle = "#0b0e14";
          ctx.fill();
        });
      }

      drawLine(errData, "rgb(248,81,73)", 0.08);
      drawLine(memData, "rgb(188,140,255)", 0.1);
      drawLine(cpuData, "rgb(99,140,255)", 0.12);

      const anomalyX = pad.left + step * 7.5;
      const anomalyW = step * 1.5;
      ctx.fillStyle = "rgba(248,81,73,0.06)";
      ctx.fillRect(anomalyX, pad.top, anomalyW, chartH);
      ctx.strokeStyle = "rgba(248,81,73,0.2)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(anomalyX, pad.top, anomalyW, chartH);
      ctx.setLineDash([]);

      ctx.fillStyle = "#f85149";
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = "center";
      ctx.fillText("anomaly", anomalyX + anomalyW / 2, pad.top - 6);
    }

    drawMetricsChart();
    window.addEventListener("resize", drawMetricsChart);
    const intervalId = setInterval(drawMetricsChart, 5000);

    return () => {
      window.removeEventListener("resize", drawMetricsChart);
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="card chart-card wide" id="metrics-chart-card">
      <div className="card-header">
        <h2 className="card-title">Live Metrics</h2>
        <div className="chart-legend">
          <span className="legend-item"><span className="legend-dot cpu"></span>CPU %</span>
          <span className="legend-item"><span className="legend-dot memory"></span>Memory %</span>
          <span className="legend-item"><span className="legend-dot errors"></span>Error Rate</span>
        </div>
      </div>
      <div className="chart-container">
        <canvas id="metrics-chart" ref={canvasRef}></canvas>
      </div>
    </div>
  );
}
"""

anomaly_feed_tsx = """import React from 'react';

export default function AnomalyFeed({ anomalies }: { anomalies: any[] }) {
  // If no real anomalies are passed yet, we can mock them based on the HTML mockup
  const feed = anomalies.length > 0 ? anomalies : [
    { service: "svc-payments", desc: "P99 latency spike — connection pool saturation after 09:58 deploy", severity: "high", time: "10:32:01" },
    { service: "svc-auth", desc: "Elevated 5xx error rate — OAuth token refresh failing intermittently", severity: "medium", time: "10:15:44" },
    { service: "svc-cache", desc: "Memory usage trending above threshold — potential leak in Redis client", severity: "medium", time: "09:58:12" },
    { service: "svc-search", desc: "CPU utilization normal — transient spike resolved autonomously", severity: "low", time: "09:40:03" },
    { service: "svc-gateway", desc: "Request queue depth increase — upstream latency propagation", severity: "low", time: "09:22:15" },
  ];

  return (
    <div className="card anomaly-feed-card" id="anomaly-feed-card">
      <div className="card-header">
        <h2 className="card-title">Anomaly Feed</h2>
        <span className="card-badge live-badge">
          <span className="pulse-dot small"></span> Live
        </span>
      </div>
      <div className="anomaly-feed" id="anomaly-feed">
        {feed.map((a, i) => (
          <div key={i} className={`anomaly-item severity-${a.severity}`}>
            <div className="anomaly-info">
              <div className="anomaly-service">{a.service}</div>
              <div className="anomaly-desc">{a.desc || a.description}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <span className={`anomaly-severity ${a.severity}`}>{a.severity}</span>
              <span className="anomaly-time">{a.time || new Date().toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

pipeline_visual_tsx = """import React from 'react';

export default function PipelineVisual() {
  return (
    <div className="card pipeline-card" id="pipeline-card">
      <div className="card-header">
        <h2 className="card-title">Multi-Agent Pipeline</h2>
        <span className="card-subtitle">Current processing state</span>
      </div>
      <div className="pipeline-visual">
        <div className="pipeline-stage completed" id="stage-collector">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          </div>
          <span className="stage-label">Metrics Collector</span>
          <span className="stage-status">Polling</span>
        </div>
        <div className="pipeline-connector completed"></div>
        <div className="pipeline-stage completed" id="stage-detector">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
          <span className="stage-label">Anomaly Detector</span>
          <span className="stage-status">Isolation Forest</span>
        </div>
        <div className="pipeline-connector completed"></div>
        <div className="pipeline-stage active" id="stage-diagnosis">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <span className="stage-label">Diagnosis Agent</span>
          <span className="stage-status processing">Processing…</span>
        </div>
        <div className="pipeline-connector"></div>
        <div className="pipeline-stage" id="stage-remediation">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
          </div>
          <span className="stage-label">Remediation Agent</span>
          <span className="stage-status">Waiting</span>
        </div>
        <div className="pipeline-connector"></div>
        <div className="pipeline-stage" id="stage-critic">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
          <span className="stage-label">Critic Agent</span>
          <span className="stage-status">Waiting</span>
        </div>
        <div className="pipeline-connector"></div>
        <div className="pipeline-stage" id="stage-policy">
          <div className="stage-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <span className="stage-label">Policy Engine</span>
          <span className="stage-status">Waiting</span>
        </div>
      </div>
    </div>
  );
}
"""

decision_table_tsx = """import React from 'react';

export default function DecisionTable({ decisions }: { decisions: any[] }) {
  const data = decisions.length > 0 ? decisions : [
    { time: "10:32:01", service: "svc-payments", anomaly: "P99 latency spike", risk: "high", confidence: 0.71, rounds: 2, outcome: "pending", action: "rollback deploy" },
    { time: "10:15:44", service: "svc-auth", anomaly: "Elevated 5xx rate", risk: "medium", confidence: 0.83, rounds: 1, outcome: "pending", action: "restart pod" },
    { time: "09:58:12", service: "svc-cache", anomaly: "Memory threshold", risk: "medium", confidence: 0.88, rounds: 1, outcome: "approved", action: "restart pod" },
    { time: "09:40:03", service: "svc-search", anomaly: "CPU transient spike", risk: "low", confidence: 0.94, rounds: 1, outcome: "auto", action: "restart pod" },
    { time: "09:22:15", service: "svc-gateway", anomaly: "Queue depth", risk: "low", confidence: 0.91, rounds: 1, outcome: "auto", action: "scale replicas" }
  ];

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
        {data.map((d, i) => (
          <tr key={i}>
            <td className="cell-mono">{d.time || new Date().toLocaleTimeString()}</td>
            <td><code style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{d.service}</code></td>
            <td>{d.anomaly || d.anomaly_type}</td>
            <td><span className={`risk-badge ${d.risk || d.risk_tier}`}>{d.risk || d.risk_tier}</span></td>
            <td className="cell-mono">{(d.confidence || 0).toFixed(2)}</td>
            <td className="cell-mono">{d.rounds}/2</td>
            <td><span className={`outcome-badge ${d.outcome}`}>{d.outcome === "auto" ? "Auto-Executed" : d.outcome?.charAt(0).toUpperCase() + d.outcome?.slice(1)}</span></td>
            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{d.action || d.final_action}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
"""

history_view_tsx = """import React, { useEffect, useState } from 'react';
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
"""

settings_view_tsx = """import React, { useEffect, useState } from 'react';
import { getSettings } from '../api';

export default function SettingsView() {
  const [settings, setSettings] = useState<any>(null);

  useEffect(() => {
    getSettings().then(res => setSettings(res.data)).catch(console.error);
  }, []);

  return (
    <section className="view active" id="view-settings">
      <div className="settings-grid">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Anomaly Detection</h2>
          </div>
          <div className="settings-form">
            <div className="setting-row">
              <label className="setting-label">Anomaly Score Threshold</label>
              <input type="number" className="setting-input" defaultValue="0.65" step="0.01" min="0" max="1" />
            </div>
            <div className="setting-row">
              <label className="setting-label">Polling Interval (seconds)</label>
              <input type="number" className="setting-input" defaultValue="15" step="1" min="5" />
            </div>
            <div className="setting-row">
              <label className="setting-label">Debate Round Cap</label>
              <input type="number" className="setting-input" defaultValue="2" step="1" min="1" max="5" />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Autonomy Policy</h2>
          </div>
          <div className="settings-form">
            <div className="setting-row">
              <label className="setting-label">Confidence Threshold (auto-execute)</label>
              <input type="number" className="setting-input" defaultValue="0.80" step="0.01" min="0" max="1" />
            </div>
            <div className="setting-row">
              <label className="setting-label">Risk Tier Assignments</label>
              <div className="risk-config">
                <div className="risk-item"><code>restart pod</code><span className="risk-badge low">Low</span></div>
                <div className="risk-item"><code>scale replicas</code><span className="risk-badge medium">Medium</span></div>
                <div className="risk-item"><code>rollback deploy</code><span className="risk-badge high">High</span></div>
                <div className="risk-item"><code>cordon node</code><span className="risk-badge high">High</span></div>
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Remediation Whitelist</h2>
          </div>
          <div className="settings-form">
            <div className="whitelist-items">
              <div className="whitelist-item"><code>kubectl rollout restart</code> <span className="wl-status enabled">Enabled</span></div>
              <div className="whitelist-item"><code>kubectl rollout undo</code> <span className="wl-status enabled">Enabled</span></div>
              <div className="whitelist-item"><code>kubectl scale</code> <span className="wl-status enabled">Enabled</span></div>
              <div className="whitelist-item"><code>kubectl cordon</code> <span className="wl-status enabled">Enabled</span></div>
              <div className="whitelist-item"><code>kubectl delete pod</code> <span className="wl-status disabled">Disabled</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
"""

escalations_view_tsx = """import React, { useEffect, useState } from 'react';
import { getEscalatedDecisions, getDecisionDetail, submitApproval } from '../api';

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
        const q = res.data?.length ? res.data : mockQueue;
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
                    <span>{esc.anomaly}</span>
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
"""

files = {
  "App.tsx": app_tsx,
  "components/Sidebar.tsx": sidebar_tsx,
  "components/TopBar.tsx": topbar_tsx,
  "views/LiveDashboard.tsx": livedashboard_tsx,
  "components/KpiCard.tsx": kpicard_tsx,
  "components/MetricsChart.tsx": metrics_chart_tsx,
  "components/AnomalyFeed.tsx": anomaly_feed_tsx,
  "components/PipelineVisual.tsx": pipeline_visual_tsx,
  "components/DecisionTable.tsx": decision_table_tsx,
  "views/HistoryView.tsx": history_view_tsx,
  "views/SettingsView.tsx": settings_view_tsx,
  "views/EscalationsView.tsx": escalations_view_tsx
}

for rel_path, content in files.items():
    full_path = os.path.join(frontend_src, rel_path)
    with open(full_path, "w") as f:
        f.write(content)

print("Created components!")

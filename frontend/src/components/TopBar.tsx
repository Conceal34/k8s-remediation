import { useEffect, useState } from 'react';

const titles: Record<string, string[]> = {
  live: ["Live Dashboard", "Real-time cluster health & anomaly detection"],
  escalations: ["Escalation Queue", "Review pending decisions requiring operator approval"],
  history: ["Decision History", "Full audit trail of all anomaly responses"],
  chaos: ["Demo Controls", "Trigger synthetic faults for autonomous remediation"],
  settings: ["Configuration", "Anomaly thresholds, policy rules & remediation whitelist"],
};

export default function TopBar({ currentView }: { currentView: string }) {
  const [timeStr, setTimeStr] = useState('');
  const [dateStr, setDateStr] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }));
      setDateStr(now.toLocaleDateString("en-GB", {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric",
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
        <div className="timestamp">
          <span className="timestamp-time">{timeStr}</span>
          <span className="timestamp-date">{dateStr}</span>
        </div>
      </div>
    </header>
  );
}

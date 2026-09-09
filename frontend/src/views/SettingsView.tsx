import { useEffect, useState } from 'react';
import { getSettings } from '../api';

export default function SettingsView() {
  const [settings, setSettings] = useState<any>(null);
  const [error, setError] = useState(false);

  const fetchSettings = () => {
    setError(false);
    getSettings()
      .then(res => setSettings(res.data))
      .catch(e => {
        console.error(e);
        setError(true);
      });
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'var(--color-danger)' }}>
        Failed to load settings. <button onClick={fetchSettings} className="btn-ghost">Retry</button>
      </div>
    );
  }

  if (!settings) return <div style={{ padding: '20px' }}>Loading settings...</div>;

  const getRiskBadge = (tier: string) => {
    const cls = tier === 'low' ? 'low' : tier === 'medium' ? 'medium' : 'high';
    return <span className={`risk-badge ${cls}`}>{tier.charAt(0).toUpperCase() + tier.slice(1)}</span>;
  };

  return (
    <section className="view active" id="view-settings">
      <div className="settings-grid">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Anomaly Detection</h2>
          </div>
          <div className="settings-form">
            <div className="setting-row">
              <label className="setting-label">LLM Model</label>
              <input type="text" className="setting-input" value={settings.llm_model || 'unknown'} readOnly />
            </div>
            <div className="setting-row">
              <label className="setting-label">Anomaly Score Threshold</label>
              <input type="number" className="setting-input" value={settings.anomaly_score_threshold || 0.65} readOnly />
            </div>
            <div className="setting-row">
              <label className="setting-label">Polling Interval (seconds)</label>
              <input type="number" className="setting-input" value={settings.polling_interval_seconds || 15} readOnly />
            </div>
            <div className="setting-row">
              <label className="setting-label">Debate Round Cap</label>
              <input type="number" className="setting-input" value={settings.max_debate_rounds || 2} readOnly />
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
              <input type="number" className="setting-input" value={settings.confidence_threshold || 0.80} readOnly />
            </div>
            <div className="setting-row">
              <label className="setting-label">Risk Tier Assignments</label>
              <div className="risk-config">
                {settings.action_risk_tiers && Object.entries(settings.action_risk_tiers).map(([action, tier]: any) => (
                  <div className="risk-item" key={action}><code>{action}</code>{getRiskBadge(tier)}</div>
                ))}
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
              {settings.whitelist && settings.whitelist.map((action: string) => (
                <div className="whitelist-item" key={action}><code>{action}</code> <span className="wl-status enabled">Enabled</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

import { useEffect, useState } from 'react';
import { getSettings } from '../api';

export default function SettingsView() {
  const [, setSettings] = useState<any>(null);

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

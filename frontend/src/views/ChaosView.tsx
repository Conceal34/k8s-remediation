import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';

const SERVICES = ['payment-service', 'order-service', 'auth-service'];
const FAULTS = [
  { id: 'cpu_spike', label: 'CPU Spike (High Load)' },
  { id: 'memory_spike', label: 'Memory Leak (OOM Risk)' },
  { id: 'crash_loop', label: 'Crash Loop (App Failing)' },
];

export default function ChaosView() {
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const [selectedService, setSelectedService] = useState(SERVICES[0]);
  const [selectedFault, setSelectedFault] = useState(FAULTS[0].id);

  const inject = async () => {
    setLoading('inject');
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/chaos/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_type: selectedFault, service: selectedService })
      });
      if (res.ok) {
        const faultLabel = FAULTS.find(f => f.id === selectedFault)?.label;
        setResult(`✓ Injected ${faultLabel} into ${selectedService}`);
      } else {
        setResult(`Failed: ${res.statusText}`);
      }
    } catch (e: any) {
      setResult(`Error: ${e.message}`);
    }
    setLoading(null);
  };

  const cleanup = async () => {
    setLoading('cleanup');
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/chaos/cleanup`, { method: 'POST' });
      if (res.ok) setResult('✓ All faults cleaned up and healed.');
    } catch (e: any) {
      setResult(`Error: ${e.message}`);
    }
    setLoading(null);
  };

  return (
    <section className="view active" id="view-chaos">
      <div className="card" style={{ maxWidth: 600, margin: 'var(--sp-8) auto', padding: 'var(--sp-8)' }}>
        <div className="card-header" style={{ marginBottom: 'var(--sp-6)' }}>
          <h2 className="card-title" style={{ fontSize: '1.2rem' }}>Chaos Controls (Demo Panel)</h2>
        </div>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 'var(--sp-6)' }}>
          Manually trigger synthetic faults to demonstrate autonomous detection and remediation without using the CLI.
        </p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          
          <div style={{ display: 'flex', gap: 'var(--sp-4)' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: 'var(--sp-2)', fontSize: '0.85rem', color: 'var(--text-tertiary)' }}>Target Service</label>
              <select 
                className="filter-select" 
                style={{ width: '100%', padding: 'var(--sp-2)' }}
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
              >
                {SERVICES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: 'var(--sp-2)', fontSize: '0.85rem', color: 'var(--text-tertiary)' }}>Fault Type</label>
              <select 
                className="filter-select" 
                style={{ width: '100%', padding: 'var(--sp-2)' }}
                value={selectedFault}
                onChange={(e) => setSelectedFault(e.target.value)}
              >
                {FAULTS.map(f => <option key={f.id} value={f.id}>{f.label}</option>)}
              </select>
            </div>
          </div>

          <button 
            className="btn btn-edit" 
            style={{ width: '100%', justifyContent: 'center', marginTop: 'var(--sp-2)' }}
            disabled={!!loading}
            onClick={inject}
          >
            {loading === 'inject' ? 'Injecting...' : 'Inject Fault'}
          </button>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-default)', margin: 'var(--sp-4) 0' }} />

          <button 
            className="btn btn-approve" 
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!!loading}
            onClick={cleanup}
          >
            {loading === 'cleanup' ? 'Cleaning up...' : 'Clear All Faults (Heal Cluster)'}
          </button>

          {result && (
            <div style={{ marginTop: 'var(--sp-4)', padding: 'var(--sp-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--r-sm)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              {result}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

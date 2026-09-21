import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';

export default function ChaosView() {
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const inject = async (type: string, service: string) => {
    setLoading(type);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/chaos/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_type: type, service })
      });
      if (res.ok) {
        setResult(`✓ Injected ${type} into ${service}`);
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
          <button 
            className="btn btn-edit" 
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!!loading}
            onClick={() => inject('cpu_spike', 'payment-service')}
          >
            {loading === 'cpu_spike' ? 'Injecting...' : 'Inject CPU Spike (Payment Service)'}
          </button>
          
          <button 
            className="btn btn-edit" 
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!!loading}
            onClick={() => inject('memory_spike', 'order-service')}
          >
            {loading === 'memory_spike' ? 'Injecting...' : 'Inject Memory Leak (Order Service)'}
          </button>
          
          <button 
            className="btn btn-edit" 
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!!loading}
            onClick={() => inject('crash_loop', 'auth-service')}
          >
            {loading === 'crash_loop' ? 'Injecting...' : 'Inject Crash Loop (Auth Service)'}
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

import React, { useState, useEffect } from 'react';
import './kimi.css';

export function KimiPanel() {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [mockMode, setMockMode] = useState(true);
  const [polling, setPolling] = useState(false);

  async function start() {
    const body = { name, phone, email, address, source: 'frontend_kimi' };
    const resp = await fetch('/api/v1/kimi/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    setRunId(data.run_id);
    setLogs([]);
    setStatus({ status: 'pending', progress: 0 });
    setPolling(true);
  }

  async function stop() {
    // currently stop is not implemented on backend; we'll just stop polling
    setPolling(false);
    setStatus((s:any)=> ({...s, status: 'stopped'}));
  }

  async function fetchStatus(rid: string) {
    const resp = await fetch(`/api/v1/kimi/status/${rid}`);
    if (!resp.ok) return;
    const data = await resp.json();
    setStatus(data);
    setLogs(data.logs || []);
    if (data.status === 'completed' || data.status === 'failed') {
      setPolling(false);
    }
  }

  useEffect(() => {
    let t: any;
    if (polling && runId) {
      t = setInterval(() => fetchStatus(runId), 600);
    }
    return () => clearInterval(t);
  }, [polling, runId]);

  async function saveConfig() {
    await fetch('/api/v1/kimi/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mock_mode: mockMode }),
    });
    alert('Config saved');
  }

  return (
    <div className="kimi-panel">
      <div className="kimi-card">
        <h3 className="kimi-title">Kimi Agent</h3>
        <div className="kimi-form">
          <input className="kimi-input" placeholder="Name" value={name} onChange={(e)=>setName(e.target.value)} />
          <input className="kimi-input" placeholder="Phone" value={phone} onChange={(e)=>setPhone(e.target.value)} />
          <input className="kimi-input" placeholder="Email" value={email} onChange={(e)=>setEmail(e.target.value)} />
          <input className="kimi-input" placeholder="Address" value={address} onChange={(e)=>setAddress(e.target.value)} />
          <div className="kimi-controls">
            <button className="kimi-btn primary" onClick={start}>Start</button>
            <button className="kimi-btn outline" onClick={stop}>Stop</button>
            <label className="kimi-switch">
              <input type="checkbox" checked={mockMode} onChange={(e)=>setMockMode(e.target.checked)} /> Mock mode
            </label>
            <button className="kimi-btn ghost" onClick={saveConfig}>Save config</button>
          </div>
        </div>
      </div>

      <div className="kimi-logs">
        <div className="kimi-log-header">
          <strong>Run</strong>
          <span className="kim-run-id">{runId ?? '—'}</span>
          <span className="kim-status">{status?.status ?? 'idle'}</span>
          <span className="kim-progress">{status?.progress ?? 0}%</span>
        </div>
        <div className="kimi-log-body">
          {logs.length === 0 && <div className="kimi-log-empty">No logs yet</div>}
          {logs.map((l:any, idx:number)=> (
            <div key={idx} className="kimi-log-entry">
              <div className="kimi-log-ts">{new Date(l.ts*1000).toLocaleTimeString()}</div>
              <div className="kimi-log-msg">{String(l.message)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default KimiPanel;

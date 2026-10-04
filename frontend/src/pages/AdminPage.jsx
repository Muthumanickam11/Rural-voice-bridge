import { useState, useEffect } from 'react';
import { api, getAdminToken, setAdminToken, errorMessage } from '../api/client';

function MetricCard({ value, label, color = 'var(--clr-primary)' }) {
  return (
    <div className="metric-card">
      <div className="metric-value" style={{ color }}>{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

function LogEntry({ log }) {
  const isEmergency = log.safety_level === 'emergency';
  const ts = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('ta-IN') : '';
  return (
    <div className={`log-entry ${isEmergency ? 'emergency' : 'success'}`}>
      <span className="log-ts">{ts}</span>
      <span className="log-badge intent">{log.intent || log.event_type}</span>
      {isEmergency && <span className="log-badge safety">🚨 EMERGENCY</span>}
      {log.latency_ms && <span className="log-badge latency">{log.latency_ms}ms</span>}
      <span style={{ color: 'var(--clr-text-subtle)', fontSize: '0.7rem' }}>req={log.request_id?.slice(-6)}</span>
    </div>
  );
}

export default function AdminPage() {
  // Initialised from storage lazily so no effect is needed to read the token.
  const [token, setToken] = useState(getAdminToken);
  const [tokenDraft, setTokenDraft] = useState(getAdminToken);
  const [metrics, setMetrics] = useState(null);
  const [logs, setLogs] = useState([]);
  // No token means there is nothing to load, so do not start in a loading state.
  const [loading, setLoading] = useState(() => Boolean(getAdminToken()));
  const [error, setError] = useState(null);

  const AUTH_ERROR =
    'அணுகல் மறுக்கப்பட்டது. சரியான நிர்வாகி ரகுப்பு (token) ஐ சரிபார்க்கவும்.';

  // Every setState here happens after an await, so calling this from an effect
  // does not synchronously update state during the effect pass.
  const fetchData = async (useToken) => {
    const [m, l] = await Promise.all([
      api.adminMetrics(useToken),
      api.adminLogs(30, useToken).catch(() => ({ logs: [] }))
    ]);
    setMetrics(m);
    setLogs(l?.logs || []);
    setError(null);
  };

  const handleRefresh = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      await fetchData(token);
    } catch (e) {
      setMetrics(null);
      setLogs([]);
      setError(errorMessage(e, AUTH_ERROR));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // With no token there is nothing to fetch, and clearing state here would be
    // a synchronous setState inside an effect; that happens in
    // handleSaveToken instead, where the change actually originates.
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        await fetchData(token);
      } catch (e) {
        if (!cancelled) setError(errorMessage(e, AUTH_ERROR));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const handleSaveToken = () => {
    const t = tokenDraft.trim();
    setAdminToken(t);
    setToken(t);
    if (!t) {
      setMetrics(null);
      setLogs([]);
      setError(null);
      setLoading(false);
    }
  };

  return (
    <div className="admin-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="page-title">📊 கண்காணிப்பு மையம்</div>
        <button
          className="btn btn-ghost"
          style={{ fontSize: '0.82rem', padding: '0.4rem 0.8rem' }}
          onClick={handleRefresh}
          disabled={!token || loading}
        >
          🔄 புதுப்பிக்க
        </button>
      </div>

      {/* Admin token gate */}
      <div className="form-group">
        <label className="form-label" htmlFor="admin-token">நிர்வாகி ரகுப்பு (Admin token)</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            id="admin-token"
            className="input"
            type="password"
            autoComplete="off"
            value={tokenDraft}
            onChange={e => setTokenDraft(e.target.value)}
            placeholder="X-Admin-Token"
          />
          <button className="btn btn-primary" onClick={handleSaveToken} style={{ whiteSpace: 'nowrap' }}>
            சேமி
          </button>
        </div>
      </div>

      {error && (
        <div className="warning-item ta" style={{ borderRadius: 'var(--radius-md)' }}>{error}</div>
      )}

      {loading && token ? (
        <div className="metrics-grid">
          {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : metrics ? (
        <div className="metrics-grid">
          <MetricCard value={metrics.total_events} label="TOTAL EVENTS" />
          <MetricCard value={metrics.emergency_events} label="EMERGENCIES" color="var(--clr-danger)" />
          <MetricCard value={`${metrics.avg_latency_ms}ms`} label="AVG LATENCY" color="var(--clr-warning)" />
          <MetricCard value={metrics.recent_audit_count} label="RECENT AUDIT" color="var(--clr-secondary)" />
        </div>
      ) : null}

      {/* Intent Breakdown */}
      {metrics?.intent_breakdown && Object.keys(metrics.intent_breakdown).length > 0 && (
        <div>
          <div className="section-title" style={{ marginBottom: '0.6rem' }}>INTENT BREAKDOWN</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
            {Object.entries(metrics.intent_breakdown).map(([intent, count]) => (
              <div key={intent} className="tag tag-blue">
                {intent}: <strong style={{ marginLeft: '0.3rem' }}>{count}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Audit Logs */}
      <div>
        <div className="section-title" style={{ marginBottom: '0.6rem' }}>RECENT AUDIT LOG ({logs.length})</div>
        {logs.length === 0 ? (
          <div style={{ color: 'var(--clr-text-subtle)', fontSize: '0.85rem', textAlign: 'center', padding: '1.5rem' }}>
            No audit events yet. Start making queries!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', maxHeight: '400px', overflowY: 'auto' }}>
            {logs.map((l, i) => <LogEntry key={i} log={l} />)}
          </div>
        )}
      </div>

      {/* KB Info */}
      <div style={{
        background: 'var(--clr-surface)',
        border: '1px solid var(--clr-border)',
        borderRadius: 'var(--radius-md)',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem'
      }}>
        <div className="section-title" style={{ borderBottom: 'none', paddingBottom: 0 }}>SYSTEM INFO</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontFamily: 'var(--font-en)', fontSize: '0.8rem', color: 'var(--clr-text-muted)' }}>
          <span>App: Rural Voice Bridge (கிராம குரல் பாலம்)</span>
          <span>API: /api/v1 → localhost:8000</span>
          {/* Swagger UI is served from the app root, not under the /api/v1 prefix. */}
          <span>Docs: <a href="/docs" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--clr-primary)' }}>/docs</a></span>
          <a className="tag tag-green" href="/api/v1/health" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', width: 'fit-content', marginTop: '0.25rem' }}>
            🟢 Health Check
          </a>
        </div>
      </div>
    </div>
  );
}

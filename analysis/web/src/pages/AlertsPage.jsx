import { useState, useEffect } from 'react';
import { getAlerts, createAlert, deleteAlert } from '../utils/api';

const CONDITIONS = [
    { value: 'above',           label: 'Price above $' },
    { value: 'below',           label: 'Price below $' },
    { value: 'change_pct_up',   label: 'Daily change ≥ +%' },
    { value: 'change_pct_down', label: 'Daily change ≤ −%' },
];

function conditionLabel(cond, threshold) {
    switch (cond) {
        case 'above':           return `Price > $${threshold}`;
        case 'below':           return `Price < $${threshold}`;
        case 'change_pct_up':   return `Change ≥ +${threshold}%`;
        case 'change_pct_down': return `Change ≤ −${threshold}%`;
        default: return `${cond} ${threshold}`;
    }
}

export default function AlertsPage() {
    const [alerts, setAlerts]         = useState([]);
    const [ticker, setTicker]         = useState('');
    const [condition, setCondition]   = useState('above');
    const [threshold, setThreshold]   = useState('');
    const [loading, setLoading]       = useState(true);
    const [loaded, setLoaded]         = useState(false);
    const [creating, setCreating]     = useState(false);
    const [error, setError]           = useState('');
    const [showAll, setShowAll]       = useState(false);

    async function load() {
        setError('');
        setLoaded(false);
        try {
            const data = await getAlerts(!showAll);
            setAlerts(data.data || []);
            setLoaded(true);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, [showAll]);

    async function handleCreate(e) {
        e.preventDefault();
        if (!ticker || !threshold) return;
        setCreating(true); setError('');
        try {
            await createAlert(ticker.trim().toUpperCase(), condition, parseFloat(threshold));
            setTicker(''); setThreshold('');
            await load();
        } catch (err) { setError(err.message); }
        finally { setCreating(false); }
    }

    async function handleDelete(id) {
        try {
            await deleteAlert(id);
            setAlerts(prev => prev.filter(a => a.id !== id));
        } catch (err) { setError(err.message); }
    }

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Alerts</h1>
                    <p className="page-subtitle">Get notified when price targets are hit</p>
                </div>
                <button
                    id="btn-toggle-show-all"
                    className="btn btn-secondary"
                    onClick={() => setShowAll(s => !s)}
                >
                    {showAll ? 'Show Active Only' : 'Show All'}
                </button>
            </div>

            {/* Create alert form */}
            <form onSubmit={handleCreate} className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Create Alert</div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <div className="input-group" style={{ width: 120 }}>
                        <label className="input-label">Ticker</label>
                        <input id="alert-ticker" className="input" placeholder="AAPL"
                            value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} />
                    </div>
                    <div className="input-group" style={{ flex: '1 1 200px' }}>
                        <label className="input-label">Condition</label>
                        <select id="alert-condition" className="select" value={condition} onChange={e => setCondition(e.target.value)}>
                            {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                    </div>
                    <div className="input-group" style={{ width: 140 }}>
                        <label className="input-label">Threshold</label>
                        <input id="alert-threshold" className="input" type="number" placeholder="150.00" step="0.01"
                            value={threshold} onChange={e => setThreshold(e.target.value)} />
                    </div>
                    <button id="btn-create-alert" className="btn btn-primary" type="submit" disabled={creating}>
                        {creating ? <span className="spinner spinner-sm" /> : '+ Create Alert'}
                    </button>
                </div>
            </form>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-md)' }}>{error}</div>}

            {loading ? (
                <div className="loading-state"><div className="spinner" /></div>
            ) : !loaded ? null : alerts.length === 0 ? (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🔔</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>No alerts set</h3>
                        <p style={{ fontSize: '0.825rem' }}>Create an alert above to get notified on price moves.</p>
                    </div>
                </div>
            ) : (
                <div className="glass-card">
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Condition</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                    <th>Triggered</th>
                                    <th style={{ width: 60 }}>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {alerts.map(a => (
                                    <tr key={a.id} style={{ opacity: a.is_triggered ? 0.6 : 1 }}>
                                        <td><span className="ticker-badge">{a.ticker}</span></td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                            {conditionLabel(a.condition, a.threshold)}
                                        </td>
                                        <td>
                                            <span className={`badge ${a.is_triggered ? 'badge-green' : 'badge-yellow'}`}>
                                                {a.is_triggered ? '✓ Triggered' : '⏳ Watching'}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            {new Date(a.created_at).toLocaleDateString()}
                                        </td>
                                        <td style={{ fontSize: '0.75rem', color: a.triggered_at ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                                            {a.triggered_at ? new Date(a.triggered_at).toLocaleString() : '—'}
                                        </td>
                                        <td>
                                            <button
                                                id={`btn-delete-alert-${a.id}`}
                                                className="btn btn-danger btn-icon"
                                                style={{ width: 28, height: 28, fontSize: '0.75rem' }}
                                                onClick={() => handleDelete(a.id)}
                                                title="Delete alert"
                                            >✕</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

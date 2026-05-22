import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
    getPortfolioStatus, getPortfolioHoldings,
    connectRobinhood, disconnectRobinhood, syncPortfolio,
    importPortfolioCSV, pnlClass, formatCurrency
} from '../utils/api';
import AllocationChart from '../components/AllocationChart';

// ── Connect Modal ──────────────────────────────────────────
function ConnectModal({ onClose, onConnected }) {
    const [tab, setTab]         = useState('robinhood'); // 'robinhood' | 'csv'
    const [username, setUser]   = useState('');
    const [password, setPass]   = useState('');
    const [otp, setOtp]         = useState('');
    const [csvText, setCsv]     = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError]     = useState('');

    async function handleRobinhood(e) {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const res = await connectRobinhood(username, password, otp);
            if (res.success) { onConnected(); onClose(); }
            else setError(res.error || 'Connection failed');
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    async function handleCSV(e) {
        e.preventDefault();
        if (!csvText.trim()) { setError('Paste your CSV data first'); return; }
        setLoading(true); setError('');
        try {
            const res = await importPortfolioCSV(csvText);
            if (res.success) { onConnected(); onClose(); }
            else setError(res.error || 'Import failed');
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, backdropFilter: 'blur(4px)'
        }}>
            <div className="glass-card" style={{ width: 440, maxWidth: '95vw', cursor: 'default' }}>
                <div className="card-header">
                    <h3 style={{ fontSize: '1rem' }}>Connect Portfolio</h3>
                    <button className="btn btn-ghost btn-icon" onClick={onClose}>✕</button>
                </div>

                <div className="tabs" style={{ marginBottom: 'var(--spacing-lg)' }}>
                    <button className={`tab-btn ${tab === 'robinhood' ? 'active' : ''}`}
                        onClick={() => setTab('robinhood')}>🏦 Robinhood</button>
                    <button className={`tab-btn ${tab === 'csv' ? 'active' : ''}`}
                        onClick={() => setTab('csv')}>📋 Manual CSV</button>
                </div>

                {tab === 'robinhood' ? (
                    <form onSubmit={handleRobinhood} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                        <div className="input-group">
                            <label className="input-label">Email</label>
                            <input id="rh-username" className="input" type="email" placeholder="you@email.com"
                                value={username} onChange={e => setUser(e.target.value)} required />
                        </div>
                        <div className="input-group">
                            <label className="input-label">Password</label>
                            <input id="rh-password" className="input" type="password" placeholder="••••••••"
                                value={password} onChange={e => setPass(e.target.value)} required />
                        </div>
                        <div className="input-group">
                            <label className="input-label">OTP / 2FA Code</label>
                            <input id="rh-otp" className="input" type="text" placeholder="6-digit code"
                                value={otp} onChange={e => setOtp(e.target.value)} maxLength={8} />
                        </div>
                        {error && <div className="alert alert-error">{error}</div>}
                        <div className="alert alert-info" style={{ fontSize: '0.75rem' }}>
                            🔒 Credentials are never stored. Only a session token is cached for 24 hours.
                        </div>
                        <button id="btn-rh-connect" className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <><span className="spinner spinner-sm" /> Connecting…</> : 'Connect Robinhood'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleCSV} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                        <div className="input-group">
                            <label className="input-label">CSV (ticker, shares, avg_cost)</label>
                            <textarea id="csv-input" className="input" rows={6}
                                style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: '0.8rem' }}
                                placeholder={"AAPL,10,145.50\nNVDA,5,480.00\nMSFT,8,320.00"}
                                value={csvText} onChange={e => setCsv(e.target.value)} />
                        </div>
                        {error && <div className="alert alert-error">{error}</div>}
                        <button id="btn-csv-import" className="btn btn-primary" type="submit" disabled={loading}>
                            {loading ? <><span className="spinner spinner-sm" /> Importing…</> : 'Import Portfolio'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}

// ── Holdings Table ─────────────────────────────────────────
function HoldingsTable({ holdings }) {
    if (!holdings?.length) return null;
    return (
        <div className="table-container" style={{ marginTop: 'var(--spacing-lg)' }}>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Shares</th>
                        <th>Avg Cost</th>
                        <th>Current Price</th>
                        <th>Current Value</th>
                        <th>P&amp;L</th>
                        <th>P&amp;L %</th>
                        <th>Weight</th>
                        <th>Source</th>
                    </tr>
                </thead>
                <tbody>
                    {holdings.map(h => (
                        <tr key={h.ticker}>
                            <td>
                                <span className="ticker-badge">{h.ticker}</span>
                            </td>
                            <td style={{ fontFamily: 'monospace' }}>{h.shares?.toFixed(4)}</td>
                            <td style={{ fontFamily: 'monospace' }}>
                                {h.avg_cost ? `$${h.avg_cost.toFixed(2)}` : '—'}
                            </td>
                            <td style={{ fontFamily: 'monospace' }}>
                                {h.current_price ? `$${h.current_price.toFixed(2)}` : '—'}
                            </td>
                            <td style={{ fontFamily: 'monospace' }}>
                                {h.current_value ? `$${h.current_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—'}
                            </td>
                            <td className={pnlClass(h.unrealized_pnl)}>
                                {h.unrealized_pnl != null
                                    ? `${h.unrealized_pnl >= 0 ? '+' : ''}$${Math.abs(h.unrealized_pnl).toFixed(2)}`
                                    : '—'}
                            </td>
                            <td className={pnlClass(h.unrealized_pnl_pct)}>
                                {h.unrealized_pnl_pct != null
                                    ? `${h.unrealized_pnl_pct >= 0 ? '+' : ''}${h.unrealized_pnl_pct.toFixed(2)}%`
                                    : '—'}
                            </td>
                            <td style={{ color: 'var(--text-secondary)' }}>
                                {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : '—'}
                            </td>
                            <td>
                                <span className={`badge ${h.source === 'robinhood' ? 'badge-green' : 'badge-gray'}`}>
                                    {h.source}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── Main Page ──────────────────────────────────────────────
export default function PortfolioPage({ onConnected }) {
    const [status, setStatus]     = useState(null);
    const [holdings, setHoldings] = useState([]);
    const [summary, setSummary]   = useState(null);
    const [showModal, setModal]   = useState(false);
    const [syncing, setSyncing]   = useState(false);
    const [loading, setLoading]   = useState(true);
    const [loaded, setLoaded]     = useState(false);
    const [error, setError]       = useState('');

    async function load() {
        setLoading(true);
        setError('');
        setLoaded(false);
        try {
            const [st, hData] = await Promise.all([getPortfolioStatus(), getPortfolioHoldings()]);
            setStatus(st);
            setHoldings(hData.holdings || []);
            setSummary(hData.summary || null);
            setLoaded(true);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, []);

    async function handleSync() {
        setSyncing(true);
        try { await syncPortfolio(); await load(); } catch (e) { setError(e.message); }
        finally { setSyncing(false); }
    }

    async function handleDisconnect() {
        try { await disconnectRobinhood(); await load(); } catch (e) { setError(e.message); }
    }

    const totalPnl = summary?.total_pnl ?? 0;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Portfolio</h1>
                    <p className="page-subtitle">Track holdings, P&L, and allocation</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
                    {status?.connected && (
                        <>
                            <button id="btn-sync" className="btn btn-secondary" onClick={handleSync} disabled={syncing}>
                                {syncing ? <><span className="spinner spinner-sm" /> Syncing…</> : '🔄 Sync'}
                            </button>
                            <button id="btn-disconnect" className="btn btn-danger" onClick={handleDisconnect}>
                                Disconnect
                            </button>
                        </>
                    )}
                    {!status?.connected && (
                        <button id="btn-connect" className="btn btn-primary" onClick={() => setModal(true)}>
                            + Connect Portfolio
                        </button>
                    )}
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            {loading ? (
                <div className="loading-state"><div className="spinner" /></div>
            ) : !loaded ? null : holdings.length === 0 ? (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">💼</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>No portfolio connected</h3>
                        <p style={{ fontSize: '0.825rem', maxWidth: 360 }}>
                            Connect your Robinhood account or paste a CSV to start tracking your holdings.
                        </p>
                        <button id="btn-connect-empty" className="btn btn-primary" onClick={() => setModal(true)}>
                            + Connect Portfolio
                        </button>
                    </div>
                </div>
            ) : (
                <>
                    {/* Summary tiles */}
                    <div className="grid grid-4" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Total Value</div>
                            <div className="stat-tile-value">{summary?.total_value_fmt || '—'}</div>
                            <div className="stat-tile-sub">{summary?.holdings_count} positions</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Total P&L</div>
                            <div className={`stat-tile-value ${totalPnl >= 0 ? 'value-positive' : 'value-negative'}`}>
                                {summary?.total_pnl_fmt || '—'}
                            </div>
                            <div className="stat-tile-sub">
                                {summary?.total_pnl_pct != null
                                    ? `${summary.total_pnl_pct >= 0 ? '+' : ''}${summary.total_pnl_pct.toFixed(2)}%`
                                    : '—'}
                            </div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Cost Basis</div>
                            <div className="stat-tile-value">
                                {summary?.total_cost_basis
                                    ? `$${summary.total_cost_basis.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                                    : '—'}
                            </div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Connection</div>
                            <div className="stat-tile-value" style={{ fontSize: '1rem', color: status?.connected ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                                {status?.connected ? '● Live' : '○ No account connected'}
                            </div>
                            <div className="stat-tile-sub">{status?.connected ? (status?.username || 'Robinhood') : ''}</div>
                        </div>
                    </div>

                    {/* Allocation chart + top holdings */}
                    {holdings.length > 0 && (
                        <div className="grid grid-2" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            <div className="glass-card">
                                <div className="card-header">
                                    <span className="card-title">Allocation</span>
                                </div>
                                <AllocationChart holdings={holdings} />
                            </div>
                            <div className="glass-card">
                                <div className="card-header">
                                    <span className="card-title">Top Positions</span>
                                </div>
                                {(summary?.top_holdings || holdings.slice(0,5)).map(h => (
                                    <div key={h.ticker} style={{
                                        display: 'flex', justifyContent: 'space-between',
                                        alignItems: 'center', padding: '8px 0',
                                        borderBottom: '1px solid var(--border-color)'
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <span className="ticker-badge">{h.ticker}</span>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <div style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                                {h.current_value ? `$${h.current_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                                            </div>
                                            <div className={`${pnlClass(h.unrealized_pnl_pct)}`} style={{ fontSize: '0.75rem' }}>
                                                {h.unrealized_pnl_pct != null
                                                    ? `${h.unrealized_pnl_pct >= 0 ? '+' : ''}${h.unrealized_pnl_pct.toFixed(2)}%`
                                                    : `${h.weight_pct?.toFixed(1) ?? '—'}%`}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Full holdings table */}
                    <div className="glass-card">
                        <div className="card-header">
                            <span className="card-title">All Holdings</span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {summary?.synced_at ? `Synced ${new Date(summary.synced_at).toLocaleTimeString()}` : ''}
                            </span>
                        </div>
                        <HoldingsTable holdings={holdings} />
                    </div>
                </>
            )}

            {showModal && createPortal(
                <ConnectModal
                    onClose={() => setModal(false)}
                    onConnected={() => { onConnected(); load(); }}
                />,
                document.body
            )}
        </div>
    );
}

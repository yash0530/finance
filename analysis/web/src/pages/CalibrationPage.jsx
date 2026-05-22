import { useState, useEffect } from 'react';
import { getCalibration } from '../utils/api';

const REC_ORDER = ['BUY', 'HOLD', 'SELL'];
const CONV_ORDER = ['HIGH', 'MEDIUM', 'LOW'];

function fmtPct(v) {
    if (v == null) return '—';
    const sign = v > 0 ? '+' : '';
    return `${sign}${v.toFixed(1)}%`;
}

function fmtRate(v) {
    if (v == null) return '—';
    return `${(v * 100).toFixed(0)}%`;
}

function CalibrationTable({ title, buckets, order, label }) {
    const keys = order.filter(k => buckets[k]).concat(Object.keys(buckets).filter(k => !order.includes(k)));
    if (keys.length === 0) {
        return (
            <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>{title}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No outcomes recorded yet.</div>
            </div>
        );
    }
    return (
        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
            <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>{title}</div>
            <table style={{ width: '100%', fontSize: '0.82rem', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                        <th style={{ textAlign: 'left',  padding: '6px 8px' }}>{label}</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>N</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>3m hit-rate</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>Avg 3m return</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>1y hit-rate</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>Avg 1y return</th>
                        <th style={{ textAlign: 'right', padding: '6px 8px' }}>Sample (3m / 1y)</th>
                    </tr>
                </thead>
                <tbody style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    {keys.map(k => {
                        const b = buckets[k];
                        return (
                            <tr key={k} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                                <td style={{ padding: '6px 8px', color: 'var(--text-primary)' }}>{k}</td>
                                <td style={{ padding: '6px 8px', textAlign: 'right' }}>{b.n}</td>
                                <td style={{ padding: '6px 8px', textAlign: 'right' }}>{fmtRate(b.win_rate_3m)}</td>
                                <td style={{ padding: '6px 8px', textAlign: 'right',
                                              color: b.avg_3m_return == null ? 'var(--text-muted)'
                                                   : b.avg_3m_return >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                    {fmtPct(b.avg_3m_return)}
                                </td>
                                <td style={{ padding: '6px 8px', textAlign: 'right' }}>{fmtRate(b.win_rate_1y)}</td>
                                <td style={{ padding: '6px 8px', textAlign: 'right',
                                              color: b.avg_1y_return == null ? 'var(--text-muted)'
                                                   : b.avg_1y_return >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                    {fmtPct(b.avg_1y_return)}
                                </td>
                                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-muted)' }}>
                                    {b.n_with_3m} / {b.n_with_1y}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

export default function CalibrationPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState('');

    function load(backfill = false) {
        if (backfill) setRefreshing(true); else setLoading(true);
        setError('');
        getCalibration(backfill)
            .then(setData)
            .catch(e => setError(e.message))
            .finally(() => { setLoading(false); setRefreshing(false); });
    }

    useEffect(() => { load(false); }, []);

    if (loading) return <div className="loading-state"><div className="spinner" /></div>;

    const byRec  = data?.by_recommendation || {};
    const byConv = data?.by_conviction || {};
    const total = data?.total ?? 0;
    const with3m = data?.with_3m_outcome ?? 0;
    const with1y = data?.with_1y_outcome ?? 0;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Calibration</h1>
                    <p className="page-subtitle">
                        Track record across recommendations — hit rates and average returns by bucket
                    </p>
                </div>
                <button
                    id="calib-refresh"
                    className="btn btn-secondary"
                    onClick={() => load(true)}
                    disabled={refreshing}
                    style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                >
                    {refreshing ? 'Backfilling…' : '↻ Backfill outcomes'}
                </button>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            <div className="grid grid-4" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="stat-tile">
                    <div className="stat-tile-label">Tracked recommendations</div>
                    <div className="stat-tile-value">{total}</div>
                    <div className="stat-tile-sub">Local-model verdicts excluded</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">With 3-month outcome</div>
                    <div className="stat-tile-value">{with3m}</div>
                    <div className="stat-tile-sub">
                        {total ? `${Math.round(with3m / total * 100)}% of sample` : '—'}
                    </div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">With 1-year outcome</div>
                    <div className="stat-tile-value">{with1y}</div>
                    <div className="stat-tile-sub">
                        {total ? `${Math.round(with1y / total * 100)}% of sample` : '—'}
                    </div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">Pending</div>
                    <div className="stat-tile-value">{total - with3m}</div>
                    <div className="stat-tile-sub">No 3-month outcome yet</div>
                </div>
            </div>

            <CalibrationTable
                title="By Recommendation"
                buckets={byRec}
                order={REC_ORDER}
                label="Recommendation"
            />

            <CalibrationTable
                title="By Conviction"
                buckets={byConv}
                order={CONV_ORDER}
                label="Conviction"
            />

            <div className="glass-card">
                <div className="card-title" style={{ marginBottom: 'var(--spacing-sm)' }}>How this is computed</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <p>
                        Every Deep Research verdict from a cloud LLM (Claude / Gemini) is
                        persisted with the price at recommendation. A daily background worker
                        fills the 1m / 3m / 6m / 1y forward return from the closing price at
                        each horizon. Local-model verdicts (Ollama) are excluded — they're
                        useful for development but noisy for calibration.
                    </p>
                    <p style={{ marginTop: 8 }}>
                        <strong>Hit rate</strong>: fraction of recommendations where the
                        direction was right (BUY  positive return, SELL  negative,
                        HOLD  within a small band). <strong>Avg return</strong>: signed
                        forward return at the horizon, regardless of direction.
                    </p>
                </div>
            </div>
        </div>
    );
}

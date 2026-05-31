import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    createPortfolioHolding,
    deletePortfolioHolding,
    formatCurrency,
    formatNumber,
    getPortfolioSummary,
    importPortfolioCsv,
    pnlClass,
    updatePortfolioHolding,
} from '../utils/api';

const EMPTY_FORM = { ticker: '', shares: '', avg_cost: '' };
const EMPTY_ARRAY = [];

function Stat({ label, value, tone = '' }) {
    return (
        <div className="glass-card" style={{ minHeight: 86, cursor: 'default' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
            <div className={tone} style={{ fontSize: '1.25rem', fontWeight: 700 }}>{value}</div>
        </div>
    );
}

function ExposureBars({ title, items, total }) {
    const rows = Object.entries(items || {}).sort((a, b) => b[1] - a[1]).slice(0, 8);
    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>{title}</div>
            {rows.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>No exposure yet.</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {rows.map(([label, value]) => {
                    const pct = total ? (value / total) * 100 : 0;
                    return (
                        <div key={label}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: '0.78rem' }}>
                                <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
                                <span>{pct.toFixed(1)}%</span>
                            </div>
                            <div style={{ height: 6, background: 'var(--bg-tertiary)', borderRadius: 4, marginTop: 4, overflow: 'hidden' }}>
                                <div style={{ width: `${Math.max(2, pct)}%`, height: '100%', background: 'var(--accent-blue)' }} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function PortfolioPage({ onSelectTicker }) {
    const [summary, setSummary] = useState(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [editingId, setEditingId] = useState(null);
    const [csvText, setCsvText] = useState('');
    const [replaceManual, setReplaceManual] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setSummary(await getPortfolioSummary(true));
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        const id = window.setTimeout(load, 0);
        return () => window.clearTimeout(id);
    }, [load]);

    const holdings = summary?.holdings || EMPTY_ARRAY;
    const positions = summary?.positions || EMPTY_ARRAY;
    const total = summary?.total_position_value || 0;

    const tickerExposure = useMemo(() => {
        const out = {};
        for (const p of positions) out[p.ticker] = p.current_value || 0;
        return out;
    }, [positions]);

    async function submitHolding(e) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);
        try {
            const payload = {
                ticker: form.ticker,
                shares: Number(form.shares),
                avg_cost: form.avg_cost === '' ? null : Number(form.avg_cost),
            };
            if (editingId) await updatePortfolioHolding(editingId, payload);
            else await createPortfolioHolding(payload);
            setForm(EMPTY_FORM);
            setEditingId(null);
            await load();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setSaving(false);
        }
    }

    async function remove(id) {
        setMessage(null);
        try {
            await deletePortfolioHolding(id);
            await load();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        }
    }

    async function importCsv() {
        setSaving(true);
        setMessage(null);
        try {
            const res = await importPortfolioCsv(csvText, replaceManual);
            setCsvText('');
            setReplaceManual(false);
            setMessage({ type: 'success', text: `Imported ${res.imported} holding${res.imported === 1 ? '' : 's'}.` });
            await load();
        } catch (e) {
            setMessage({ type: 'error', text: e.message });
        } finally {
            setSaving(false);
        }
    }

    function startEdit(h) {
        setEditingId(h.id);
        setForm({
            ticker: h.ticker,
            shares: String(h.shares ?? ''),
            avg_cost: h.avg_cost == null ? '' : String(h.avg_cost),
        });
    }

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Portfolio</h1>
                    <p className="page-subtitle">Manual holdings, cost basis, and pull-time exposure</p>
                </div>
                <button className="btn btn-secondary" onClick={load} disabled={loading}>
                    {loading ? <><span className="spinner spinner-sm" /> Refreshing</> : 'Refresh'}
                </button>
            </div>

            {message && <div className={`alert alert-${message.type}`} style={{ marginBottom: 'var(--spacing-md)' }}>{message.text}</div>}

            <div className="grid grid-4" style={{ gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
                <Stat label="Position Value" value={formatCurrency(total)} />
                <Stat label="Cost Basis" value={formatCurrency(summary?.total_cost_basis || 0)} />
                <Stat
                    label="Known Gain/Loss"
                    value={summary?.known_unrealized_gain == null ? 'N/A' : `${formatCurrency(summary.known_unrealized_gain)} (${formatNumber(summary.known_unrealized_gain_pct, 1)}%)`}
                    tone={pnlClass(summary?.known_unrealized_gain)}
                />
                <Stat label="Positions" value={`${summary?.position_count || 0}`} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 'var(--spacing-lg)', alignItems: 'start' }}>
                <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                    <form className="glass-card" onSubmit={submitHolding} style={{ cursor: 'default' }}>
                        <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                            {editingId ? 'Edit Holding' : 'Add Holding'}
                        </div>
                        <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
                            <div className="input-group">
                                <label className="input-label">Ticker</label>
                                <input className="input" value={form.ticker} onChange={e => setForm(f => ({ ...f, ticker: e.target.value.toUpperCase() }))} placeholder="NVDA" />
                            </div>
                            <div className="grid grid-2" style={{ gap: 'var(--spacing-sm)' }}>
                                <div className="input-group">
                                    <label className="input-label">Shares</label>
                                    <input className="input" type="number" min="0" step="any" value={form.shares} onChange={e => setForm(f => ({ ...f, shares: e.target.value }))} />
                                </div>
                                <div className="input-group">
                                    <label className="input-label">Average Cost</label>
                                    <input className="input" type="number" min="0" step="any" value={form.avg_cost} onChange={e => setForm(f => ({ ...f, avg_cost: e.target.value }))} />
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                <button className="btn btn-primary" type="submit" disabled={saving || !form.ticker || !form.shares}>
                                    {saving ? <><span className="spinner spinner-sm" /> Saving</> : (editingId ? 'Save' : 'Add')}
                                </button>
                                {editingId && (
                                    <button className="btn btn-secondary" type="button" onClick={() => { setEditingId(null); setForm(EMPTY_FORM); }}>
                                        Cancel
                                    </button>
                                )}
                            </div>
                        </div>
                    </form>

                    <div className="glass-card" style={{ cursor: 'default' }}>
                        <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>CSV Import</div>
                        <textarea
                            className="input"
                            value={csvText}
                            onChange={e => setCsvText(e.target.value)}
                            placeholder="ticker,shares,avg_cost&#10;NVDA,2,850"
                            rows={5}
                            style={{ resize: 'vertical', minHeight: 112, fontFamily: 'JetBrains Mono, monospace' }}
                        />
                        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                            <input type="checkbox" checked={replaceManual} onChange={e => setReplaceManual(e.target.checked)} />
                            Replace manual rows
                        </label>
                        <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={importCsv} disabled={saving || !csvText.trim()}>
                            Import
                        </button>
                    </div>

                    <ExposureBars title="Theme Exposure" items={summary?.theme_exposure} total={total} />
                </section>

                <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                    <div className="glass-card" style={{ cursor: 'default', overflowX: 'auto' }}>
                        <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Holdings</div>
                        {loading && <div className="loading-state"><div className="spinner" /></div>}
                        {!loading && holdings.length === 0 && (
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No holdings added.</div>
                        )}
                        {!loading && holdings.length > 0 && (
                            <table className="data-table" style={{ minWidth: 760 }}>
                                <thead>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Shares</th>
                                        <th>Avg Cost</th>
                                        <th>Source</th>
                                        <th>Updated</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {holdings.map(h => (
                                        <tr key={h.id}>
                                            <td>
                                                <button
                                                    onClick={() => onSelectTicker?.(h.ticker)}
                                                    style={{ background: 'transparent', border: 0, color: 'var(--accent-blue-bright)', cursor: 'pointer', fontWeight: 700 }}
                                                >
                                                    {h.ticker}
                                                </button>
                                            </td>
                                            <td>{formatNumber(h.shares, 4)}</td>
                                            <td>{h.avg_cost == null ? 'N/A' : formatCurrency(h.avg_cost)}</td>
                                            <td>{h.source}</td>
                                            <td style={{ color: 'var(--text-muted)' }}>{h.synced_at ? new Date(h.synced_at).toLocaleString() : 'N/A'}</td>
                                            <td>
                                                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                                                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.72rem' }} onClick={() => startEdit(h)}>Edit</button>
                                                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.72rem' }} onClick={() => remove(h.id)}>Delete</button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--spacing-lg)' }}>
                        <ExposureBars title="Ticker Exposure" items={tickerExposure} total={total} />
                        <ExposureBars title="Source Exposure" items={summary?.source_exposure} total={total} />
                    </div>
                </section>
            </div>
        </div>
    );
}

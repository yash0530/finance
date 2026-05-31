import { useEffect, useMemo, useState } from 'react';
import {
    formatPercent,
    getCalibrationDashboard,
    refreshCalibrationOutcomes,
    updateRecommendationOutcome,
} from '../utils/api';

function fmt(value) {
    return value == null ? 'N/A' : formatPercent(value, true);
}

function badgeFor(status) {
    if (status === 'due') return 'badge-yellow';
    if (status === 'reviewed') return 'badge-green';
    return 'badge-gray';
}

function Stat({ label, value, sub }) {
    return (
        <div className="stat-tile">
            <div className="stat-tile-label">{label}</div>
            <div className="stat-tile-value">{value ?? 'N/A'}</div>
            {sub && <div className="stat-tile-sub">{sub}</div>}
        </div>
    );
}

function GroupTable({ title, rows }) {
    return (
        <section>
            <div className="card-header">
                <h2 className="card-title">{title}</h2>
            </div>
            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Group</th>
                            <th>Total</th>
                            <th>Reviewed</th>
                            <th>Due</th>
                            <th>Favorable</th>
                            <th>Avg 3m</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(rows || []).slice(0, 8).map(row => (
                            <tr key={row.key}>
                                <td>{row.key}</td>
                                <td>{row.total_recommendations}</td>
                                <td>{row.reviewed}</td>
                                <td>{row.due_for_review}</td>
                                <td>{fmt(row.favorable_rate)}</td>
                                <td>{fmt(row.avg_3m_return_pct)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

export default function CalibrationPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [ticker, setTicker] = useState('');
    const [selected, setSelected] = useState(null);
    const [form, setForm] = useState({
        outcome_1m_return_pct: '',
        outcome_3m_return_pct: '',
        outcome_6m_return_pct: '',
        outcome_1y_return_pct: '',
        outcome_thesis_falsified: '',
        outcome_notes: '',
    });

    async function load(nextTicker = ticker) {
        setLoading(true);
        setError(null);
        try {
            setData(await getCalibrationDashboard({ ticker: nextTicker.trim(), limit: 500 }));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        const id = window.setTimeout(() => load(''), 0);
        return () => window.clearTimeout(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const summary = data?.summary || {};
    const queue = data?.review_queue || [];
    const recent = data?.recent || [];

    const selectedIds = useMemo(() => (
        selected ? [selected.id] : null
    ), [selected]);

    function choose(rec) {
        setSelected(rec);
        setForm({
            outcome_1m_return_pct: rec.outcome_1m_return_pct ?? '',
            outcome_3m_return_pct: rec.outcome_3m_return_pct ?? '',
            outcome_6m_return_pct: rec.outcome_6m_return_pct ?? '',
            outcome_1y_return_pct: rec.outcome_1y_return_pct ?? '',
            outcome_thesis_falsified: rec.outcome_thesis_falsified == null ? '' : String(Boolean(rec.outcome_thesis_falsified)),
            outcome_notes: rec.outcome_notes || '',
        });
    }

    async function saveOutcome(e) {
        e.preventDefault();
        if (!selected) return;
        setError(null);
        try {
            await updateRecommendationOutcome(selected.id, form);
            setSelected(null);
            await load();
        } catch (err) {
            setError(err.message);
        }
    }

    async function refreshOutcomes() {
        setRefreshing(true);
        setError(null);
        try {
            await refreshCalibrationOutcomes(selectedIds);
            await load();
        } catch (e) {
            setError(e.message);
        } finally {
            setRefreshing(false);
        }
    }

    return (
        <div className="fade-in">
            <div className="page-header" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div>
                    <h1 className="page-title">Review & Calibration</h1>
                    <p className="page-subtitle">Saved verdict outcomes and model track record</p>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <input
                        className="input"
                        value={ticker}
                        onChange={e => setTicker(e.target.value.toUpperCase())}
                        onKeyDown={e => { if (e.key === 'Enter') load(); }}
                        placeholder="Ticker"
                        style={{ width: 120 }}
                    />
                    <button className="btn btn-secondary" onClick={() => load()} disabled={loading}>
                        {loading ? <span className="spinner spinner-sm" /> : 'Load'}
                    </button>
                    <button className="btn btn-primary" onClick={refreshOutcomes} disabled={refreshing}>
                        {refreshing ? <span className="spinner spinner-sm" /> : 'Refresh outcomes'}
                    </button>
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-md)' }}>{error}</div>}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
                <Stat label="Recommendations" value={summary.total_recommendations || 0} sub={`${summary.reviewed || 0} reviewed`} />
                <Stat label="Due" value={summary.due_for_review || 0} sub={`${summary.unreviewed || 0} unreviewed`} />
                <Stat label="Favorable" value={fmt(summary.favorable_rate)} sub="directional hit rate" />
                <Stat label="Avg 3m" value={fmt(summary.avg_3m_return_pct)} sub="reviewed calls" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--spacing-lg)', alignItems: 'start' }}>
                <section>
                    <div className="card-header">
                        <h2 className="card-title">Due Reviews</h2>
                    </div>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Call</th>
                                    <th>Conviction</th>
                                    <th>Age</th>
                                    <th>1m</th>
                                    <th>3m</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {queue.length === 0 && (
                                    <tr><td colSpan="7" style={{ color: 'var(--text-muted)' }}>No due reviews</td></tr>
                                )}
                                {queue.map(rec => (
                                    <tr key={rec.id}>
                                        <td><span className="ticker-badge">{rec.ticker}</span></td>
                                        <td>{rec.recommendation}</td>
                                        <td>{rec.conviction}</td>
                                        <td>{rec.created_at_days_old ?? 'N/A'}d</td>
                                        <td>{fmt(rec.outcome_1m_return_pct)}</td>
                                        <td>{fmt(rec.outcome_3m_return_pct)}</td>
                                        <td>
                                            <button className="btn btn-secondary" onClick={() => choose(rec)}>Mark</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <form className="glass-card" onSubmit={saveOutcome}>
                    <div className="card-header">
                        <h2 className="card-title">Manual Outcome</h2>
                        {selected && <span className="ticker-badge">{selected.ticker}</span>}
                    </div>
                    {!selected && <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem' }}>No selection</p>}
                    {selected && (
                        <div style={{ display: 'grid', gap: 10 }}>
                            {['outcome_1m_return_pct', 'outcome_3m_return_pct', 'outcome_6m_return_pct', 'outcome_1y_return_pct'].map(field => (
                                <label className="input-group" key={field}>
                                    <span className="input-label">{field.replace('outcome_', '').replace('_return_pct', '').toUpperCase()} return %</span>
                                    <input
                                        className="input"
                                        type="number"
                                        step="0.01"
                                        value={form[field]}
                                        onChange={e => setForm(prev => ({ ...prev, [field]: e.target.value }))}
                                    />
                                </label>
                            ))}
                            <label className="input-group">
                                <span className="input-label">Thesis falsified</span>
                                <select
                                    className="select"
                                    value={form.outcome_thesis_falsified}
                                    onChange={e => setForm(prev => ({ ...prev, outcome_thesis_falsified: e.target.value }))}
                                >
                                    <option value="">Unmarked</option>
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                            </label>
                            <label className="input-group">
                                <span className="input-label">Notes</span>
                                <textarea
                                    className="input"
                                    rows="3"
                                    value={form.outcome_notes}
                                    onChange={e => setForm(prev => ({ ...prev, outcome_notes: e.target.value }))}
                                />
                            </label>
                            <button className="btn btn-primary" type="submit">Save outcome</button>
                        </div>
                    )}
                </form>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--spacing-lg)', marginTop: 'var(--spacing-xl)' }}>
                <GroupTable title="By Conviction" rows={data?.by_conviction} />
                <GroupTable title="By Model" rows={data?.by_model} />
            </div>

            <section style={{ marginTop: 'var(--spacing-xl)' }}>
                <div className="card-header">
                    <h2 className="card-title">Recent Calls</h2>
                </div>
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Call</th>
                                <th>Conviction</th>
                                <th>Status</th>
                                <th>Model</th>
                                <th>1m</th>
                                <th>3m</th>
                                <th>Falsified</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recent.map(rec => (
                                <tr key={rec.id}>
                                    <td><span className="ticker-badge">{rec.ticker}</span></td>
                                    <td>{rec.recommendation}</td>
                                    <td>{rec.conviction}</td>
                                    <td><span className={`badge ${badgeFor(rec.review_status)}`}>{rec.review_status}</span></td>
                                    <td>{rec.model_key}</td>
                                    <td>{fmt(rec.outcome_1m_return_pct)}</td>
                                    <td>{fmt(rec.outcome_3m_return_pct)}</td>
                                    <td>{rec.outcome_thesis_falsified == null ? 'N/A' : rec.outcome_thesis_falsified ? 'Yes' : 'No'}</td>
                                </tr>
                            ))}
                            {!loading && recent.length === 0 && (
                                <tr><td colSpan="8" style={{ color: 'var(--text-muted)' }}>No tracked recommendations</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}

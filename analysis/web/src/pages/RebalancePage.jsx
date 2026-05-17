import { useState, useEffect } from 'react';
import { getRebalanceAnalysis } from '../utils/api';

const PROFILE_LABELS = {
    conservative: 'Conservative',
    moderate:     'Moderate',
    aggressive:   'Aggressive',
};

const urgencyColors = { high: 'badge-red', medium: 'badge-yellow', low: 'badge-blue' };
const actionColors  = {
    TRIM:   'badge-red',
    EXIT:   'badge-red',
    ADD:    'badge-green',
    HOLD:   'badge-gray',
    REVIEW: 'badge-yellow',
};
const sourceLabel = {
    research:   'Research-driven',
    mechanical: 'Risk-rule',
};

function ResearchChip({ research }) {
    if (!research) return null;
    const stale = research.stale;
    const age = research.age_days != null ? `${research.age_days}d` : '—';
    return (
        <details style={{
            marginTop: 8,
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            fontSize: '0.75rem',
        }}>
            <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <span className="badge badge-purple" style={{ marginRight: 8 }}>
                    {research.recommendation} · {research.conviction}
                </span>
                <span style={{ color: stale ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                    {stale ? `⚠ stale (${age})` : `Research age: ${age}`}
                </span>
            </summary>
            <div style={{ marginTop: 6, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {research.thesis_summary && (
                    <div style={{ marginBottom: 6 }}>
                        <strong>Thesis:</strong> {research.thesis_summary}
                    </div>
                )}
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontFamily: 'JetBrains Mono, monospace' }}>
                    {research.price_at_recommendation != null && (
                        <span>Price@rec: ${research.price_at_recommendation.toFixed(2)}</span>
                    )}
                    {research.target_low != null && research.target_high != null && (
                        <span>Target: ${research.target_low}–${research.target_high}</span>
                    )}
                    {research.stop_loss != null && (
                        <span>Stop: ${research.stop_loss}</span>
                    )}
                </div>
                {research.report_id && (
                    <div style={{ marginTop: 6, color: 'var(--text-muted)' }}>
                        Report: <code>{research.report_id}</code>
                    </div>
                )}
            </div>
        </details>
    );
}

export default function RebalancePage() {
    const [profile, setProfile]   = useState('moderate');
    const [data, setData]         = useState(null);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState('');

    useEffect(() => {
        setLoading(true);
        setError('');
        getRebalanceAnalysis(profile)
            .then(setData)
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, [profile]);

    if (loading && !data) return <div className="loading-state"><div className="spinner" /></div>;

    const holdings = data?.holdings || [];
    const summary  = data?.summary;
    const actions  = data?.actions || [];
    const issues   = data?.issues  || [];
    const coverage = data?.research_coverage || { with_research: 0, without_research: 0 };
    const rules    = data?.rules || {};
    const maxSingle = rules.max_single ?? 15;
    const minPositions = rules.min_positions ?? 10;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Rebalance</h1>
                    <p className="page-subtitle">
                        Portfolio actions driven by your latest Deep Research verdicts
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Risk profile:</span>
                    {Object.entries(PROFILE_LABELS).map(([key, label]) => (
                        <button
                            key={key}
                            id={`profile-${key}`}
                            className={`btn ${profile === key ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ padding: '4px 12px', fontSize: '0.78rem' }}
                            onClick={() => setProfile(key)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            {holdings.length === 0 ? (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">⚖️</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>No portfolio data</h3>
                        <p style={{ fontSize: '0.825rem' }}>Connect a portfolio on the Portfolio page first.</p>
                    </div>
                </div>
            ) : (
                <>
                    <div className="grid grid-4" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Portfolio Value</div>
                            <div className="stat-tile-value">{summary?.total_value_fmt || '—'}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Positions</div>
                            <div className="stat-tile-value">{holdings.length}</div>
                            <div className="stat-tile-sub">Min recommended: {minPositions}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Research Coverage</div>
                            <div className="stat-tile-value">
                                {coverage.with_research}/{coverage.with_research + coverage.without_research}
                            </div>
                            <div className="stat-tile-sub">
                                {coverage.without_research} without research
                            </div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">High Priority</div>
                            <div className={`stat-tile-value ${actions.filter(a => a.urgency === 'high').length ? 'value-negative' : 'value-positive'}`}>
                                {actions.filter(a => a.urgency === 'high').length}
                            </div>
                        </div>
                    </div>

                    {actions.length > 0 ? (
                        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                                Recommended Actions
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                                {actions.map((a, i) => (
                                    <div key={i} style={{
                                        padding: 'var(--spacing-sm) var(--spacing-md)',
                                        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)',
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
                                            <span className={`badge ${actionColors[a.action] || 'badge-gray'}`} style={{ width: 60, justifyContent: 'center' }}>
                                                {a.action}
                                            </span>
                                            {a.ticker && <span className="ticker-badge">{a.ticker}</span>}
                                            <span style={{ flex: 1, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                                                {a.reason}
                                            </span>
                                            <span className="badge badge-gray" style={{ fontSize: '0.68rem' }}>
                                                {sourceLabel[a.source] || a.source}
                                            </span>
                                            <span className={`badge ${urgencyColors[a.urgency]}`}>
                                                {a.urgency}
                                            </span>
                                        </div>
                                        <ResearchChip research={a.research} />
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="alert alert-success" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            ✅ Portfolio looks well-balanced for your {PROFILE_LABELS[profile].toLowerCase()} risk profile.
                        </div>
                    )}

                    {issues.length > 0 && (
                        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                                Risk Issues ({issues.length})
                            </div>
                            <ul style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', paddingLeft: '1.2rem' }}>
                                {issues.map((iss, i) => (
                                    <li key={i} style={{ marginBottom: 4 }}>
                                        {iss.type === 'overweight'
                                            ? `${iss.ticker} at ${iss.pct.toFixed(1)}% exceeds ${maxSingle}% cap`
                                            : iss.type === 'underdiversified'
                                                ? `Only ${iss.count} positions — below ${iss.min} minimum`
                                                : JSON.stringify(iss)}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="glass-card">
                        <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                            Position Weights vs Limit ({maxSingle}%)
                        </div>
                        {holdings.map(h => {
                            const pct = h.weight_pct || 0;
                            const overLimit = pct > maxSingle;
                            return (
                                <div key={h.ticker} style={{ marginBottom: 12 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: '0.8rem' }}>
                                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                            <span className="ticker-badge">{h.ticker}</span>
                                            <span style={{ color: 'var(--text-muted)' }}>
                                                {h.current_value ? `$${h.current_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : ''}
                                            </span>
                                        </div>
                                        <span style={{ fontFamily: 'monospace', color: overLimit ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                                            {pct.toFixed(1)}%
                                            {overLimit && ' ⚠️'}
                                        </span>
                                    </div>
                                    <div className="sentiment-bar-track">
                                        <div style={{
                                            height: '100%',
                                            width: `${Math.min(pct / maxSingle * 100, 100)}%`,
                                            background: overLimit ? 'var(--accent-red)' : 'var(--gradient-primary)',
                                            borderRadius: 'var(--radius-pill)',
                                            transition: 'width 0.5s ease',
                                        }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </>
            )}
        </div>
    );
}

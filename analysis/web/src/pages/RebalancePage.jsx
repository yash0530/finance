import { useState, useEffect } from 'react';
import { getPortfolioHoldings, getResearchReport } from '../utils/api';

const RISK_PROFILES = {
    conservative:  { label: 'Conservative',  maxSingle: 10, maxSector: 25, minPositions: 15 },
    moderate:      { label: 'Moderate',       maxSingle: 15, maxSector: 35, minPositions: 10 },
    aggressive:    { label: 'Aggressive',     maxSingle: 25, maxSector: 50, minPositions: 5  },
};

function analyzePortfolio(holdings, profile) {
    if (!holdings?.length) return null;

    const rules = RISK_PROFILES[profile];
    const total  = holdings.reduce((s, h) => s + (h.current_value || 0), 0);
    const issues = [];
    const actions = [];

    // Over-concentration check
    for (const h of holdings) {
        const pct = h.weight_pct || ((h.current_value || 0) / total * 100);
        if (pct > rules.maxSingle) {
            issues.push({ type: 'overweight', ticker: h.ticker, pct: pct.toFixed(1) });
            actions.push({
                action: 'TRIM',
                ticker: h.ticker,
                reason: `${pct.toFixed(1)}% weight exceeds ${rules.maxSingle}% limit`,
                urgency: pct > rules.maxSingle * 1.5 ? 'high' : 'medium',
            });
        }
    }

    // Under-diversified
    if (holdings.length < rules.minPositions) {
        issues.push({ type: 'underdiversified', count: holdings.length, min: rules.minPositions });
        actions.push({
            action: 'ADD',
            ticker: null,
            reason: `Only ${holdings.length} positions — consider adding more for diversification`,
            urgency: 'low',
        });
    }

    // Biggest losers
    const bigLosers = holdings
        .filter(h => h.unrealized_pnl_pct != null && h.unrealized_pnl_pct < -20)
        .sort((a, b) => a.unrealized_pnl_pct - b.unrealized_pnl_pct);

    for (const h of bigLosers) {
        actions.push({
            action: 'REVIEW',
            ticker: h.ticker,
            reason: `Down ${h.unrealized_pnl_pct.toFixed(1)}% — evaluate thesis or cut loss`,
            urgency: h.unrealized_pnl_pct < -35 ? 'high' : 'medium',
        });
    }

    return { issues, actions: actions.sort((a, b) => ({ high: 0, medium: 1, low: 2 }[a.urgency] - { high: 0, medium: 1, low: 2 }[b.urgency])) };
}

const urgencyColors = { high: 'badge-red', medium: 'badge-yellow', low: 'badge-blue' };
const actionColors  = { TRIM: 'badge-red', ADD: 'badge-green', REVIEW: 'badge-yellow' };

export default function RebalancePage() {
    const [holdings, setHoldings] = useState([]);
    const [summary, setSummary]   = useState(null);
    const [profile, setProfile]   = useState('moderate');
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState('');

    useEffect(() => {
        getPortfolioHoldings()
            .then(d => { setHoldings(d.holdings || []); setSummary(d.summary); })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (holdings.length > 0) {
            setAnalysis(analyzePortfolio(holdings, profile));
        }
    }, [holdings, profile]);

    if (loading) return <div className="loading-state"><div className="spinner" /></div>;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Rebalance</h1>
                    <p className="page-subtitle">Portfolio optimization recommendations</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Risk profile:</span>
                    {Object.entries(RISK_PROFILES).map(([key, val]) => (
                        <button
                            key={key}
                            id={`profile-${key}`}
                            className={`btn ${profile === key ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ padding: '4px 12px', fontSize: '0.78rem' }}
                            onClick={() => setProfile(key)}
                        >
                            {val.label}
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
                    {/* Summary */}
                    <div className="grid grid-4" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Portfolio Value</div>
                            <div className="stat-tile-value">{summary?.total_value_fmt || '—'}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Positions</div>
                            <div className="stat-tile-value">{holdings.length}</div>
                            <div className="stat-tile-sub">Min recommended: {RISK_PROFILES[profile].minPositions}</div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">Issues Found</div>
                            <div className={`stat-tile-value ${analysis?.issues?.length ? 'value-negative' : 'value-positive'}`}>
                                {analysis?.issues?.length ?? 0}
                            </div>
                        </div>
                        <div className="stat-tile">
                            <div className="stat-tile-label">High Priority</div>
                            <div className={`stat-tile-value ${analysis?.actions?.filter(a => a.urgency === 'high').length ? 'value-negative' : 'value-positive'}`}>
                                {analysis?.actions?.filter(a => a.urgency === 'high').length ?? 0}
                            </div>
                        </div>
                    </div>

                    {/* Action items */}
                    {analysis?.actions?.length > 0 && (
                        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                                Recommended Actions
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                                {analysis.actions.map((a, i) => (
                                    <div key={i} style={{
                                        display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)',
                                        padding: 'var(--spacing-sm) var(--spacing-md)',
                                        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)',
                                    }}>
                                        <span className={`badge ${actionColors[a.action]}`} style={{ width: 60, justifyContent: 'center' }}>
                                            {a.action}
                                        </span>
                                        {a.ticker && <span className="ticker-badge">{a.ticker}</span>}
                                        <span style={{ flex: 1, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                                            {a.reason}
                                        </span>
                                        <span className={`badge ${urgencyColors[a.urgency]}`}>
                                            {a.urgency}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {!analysis?.actions?.length && (
                        <div className="alert alert-success" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            ✅ Portfolio looks well-balanced for your {RISK_PROFILES[profile].label.toLowerCase()} risk profile.
                        </div>
                    )}

                    {/* Holdings with weight bars */}
                    <div className="glass-card">
                        <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                            Position Weights vs Limit ({RISK_PROFILES[profile].maxSingle}%)
                        </div>
                        {holdings.map(h => {
                            const pct = h.weight_pct || 0;
                            const overLimit = pct > RISK_PROFILES[profile].maxSingle;
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
                                            width: `${Math.min(pct / RISK_PROFILES[profile].maxSingle * 100, 100)}%`,
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

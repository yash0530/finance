import { useState, useEffect } from 'react';
import { getAdvisorDigest, runAdvisorDigest, getRebalanceAnalysis } from '../utils/api';

const SEVERITY_COLOR = {
    high:   'badge-red',
    medium: 'badge-yellow',
    low:    'badge-blue',
};

const ACTION_COLOR = {
    EXIT:   'badge-red',
    TRIM:   'badge-red',
    ADD:    'badge-green',
    HOLD:   'badge-gray',
    REVIEW: 'badge-yellow',
};

function DigestItem({ item }) {
    return (
        <div style={{
            padding: 'var(--spacing-sm) var(--spacing-md)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--spacing-sm)',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
                <span className="ticker-badge">{item.ticker}</span>
                <span className={`badge ${SEVERITY_COLOR[item.severity] || 'badge-gray'}`}>
                    {item.severity}
                </span>
                <span style={{ flex: 1, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {item.signal_summary || '—'}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {item.checked_at?.slice(11, 16) || ''}
                </span>
            </div>
            {item.triggered_criteria?.length > 0 && (
                <div style={{ marginTop: 6, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Triggered: {item.triggered_criteria.join('; ')}
                </div>
            )}
            {item.evidence_summary && (
                <div style={{ marginTop: 4, fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    Evidence: {item.evidence_summary}
                </div>
            )}
        </div>
    );
}

export default function AdvisorPage() {
    const [digests, setDigests]   = useState([]);
    const [rebalance, setRebalance] = useState(null);
    const [loading, setLoading]   = useState(true);
    const [running, setRunning]   = useState(false);
    const [error, setError]       = useState('');

    function load() {
        setLoading(true);
        Promise.all([
            getAdvisorDigest(7).catch(e => { setError(e.message); return { digests: [] }; }),
            getRebalanceAnalysis('moderate').catch(() => null),
        ]).then(([d, r]) => {
            setDigests(d.digests || []);
            setRebalance(r);
        }).finally(() => setLoading(false));
    }

    useEffect(() => { load(); }, []);

    async function handleRunDigest() {
        setRunning(true);
        setError('');
        try {
            await runAdvisorDigest();
            load();
        } catch (e) {
            setError(e.message);
        } finally {
            setRunning(false);
        }
    }

    const allItems = digests.flatMap(d => (d.items || []).map(i => ({ ...i, digest_date: d.digest_date })));
    const decayedItems = allItems.filter(i => i.decayed);
    const highSev = decayedItems.filter(i => i.severity === 'high').length;
    const actions = rebalance?.actions || [];
    const headlineActions = actions.filter(a => a.urgency === 'high' || a.action === 'EXIT').slice(0, 5);

    if (loading) return <div className="loading-state"><div className="spinner" /></div>;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Advisor</h1>
                    <p className="page-subtitle">
                        Decay signals, headline actions, and open questions across your positions
                    </p>
                </div>
                <button
                    id="advisor-run-digest"
                    className="btn btn-primary"
                    onClick={handleRunDigest}
                    disabled={running}
                    style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                >
                    {running ? 'Running…' : '↻ Run digest now'}
                </button>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            <div className="grid grid-4" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="stat-tile">
                    <div className="stat-tile-label">Decay signals (7d)</div>
                    <div className={`stat-tile-value ${decayedItems.length ? 'value-negative' : 'value-positive'}`}>
                        {decayedItems.length}
                    </div>
                    <div className="stat-tile-sub">{highSev} high-severity</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">Headline actions</div>
                    <div className={`stat-tile-value ${headlineActions.length ? 'value-negative' : 'value-positive'}`}>
                        {headlineActions.length}
                    </div>
                    <div className="stat-tile-sub">EXIT or high-urgency</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">Research coverage</div>
                    <div className="stat-tile-value">
                        {rebalance?.research_coverage?.with_research ?? 0}
                        /
                        {(rebalance?.research_coverage?.with_research ?? 0) +
                         (rebalance?.research_coverage?.without_research ?? 0)}
                    </div>
                    <div className="stat-tile-sub">Holdings with research</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-tile-label">Portfolio</div>
                    <div className="stat-tile-value">{rebalance?.summary?.total_value_fmt || '—'}</div>
                    <div className="stat-tile-sub">{rebalance?.holdings?.length || 0} positions</div>
                </div>
            </div>

            <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                    Headline Actions ({headlineActions.length})
                </div>
                {headlineActions.length === 0 ? (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        No high-urgency actions right now.
                    </div>
                ) : (
                    headlineActions.map((a, i) => (
                        <div key={i} style={{
                            display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)',
                            padding: 'var(--spacing-sm)',
                            borderBottom: '1px solid var(--border-subtle)',
                        }}>
                            <span className={`badge ${ACTION_COLOR[a.action] || 'badge-gray'}`} style={{ width: 60, justifyContent: 'center' }}>
                                {a.action}
                            </span>
                            {a.ticker && <span className="ticker-badge">{a.ticker}</span>}
                            <span style={{ flex: 1, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                                {a.reason}
                            </span>
                        </div>
                    ))
                )}
            </div>

            <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                    Recent Decay Signals ({decayedItems.length})
                </div>
                {decayedItems.length === 0 ? (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        No thesis-decay signals in the last 7 days. The hourly monitor
                        flags positions when recent news plausibly triggers a
                        "what would change my mind" criterion from your research.
                    </div>
                ) : (
                    decayedItems
                        .sort((a, b) => ({ high: 0, medium: 1, low: 2 }[a.severity] - { high: 0, medium: 1, low: 2 }[b.severity]))
                        .map((item, i) => <DigestItem key={i} item={item} />)
                )}
            </div>

            <div className="glass-card">
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                    Open Questions
                </div>
                <ul style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', paddingLeft: '1.2rem' }}>
                    {(rebalance?.research_coverage?.without_research ?? 0) > 0 && (
                        <li>
                            {rebalance.research_coverage.without_research} held position(s)
                            have no Deep Research on file. Run research before relying
                            on mechanical-only sizing.
                        </li>
                    )}
                    {decayedItems.some(i => i.severity === 'high') && (
                        <li>
                            At least one high-severity decay signal. Open the Rebalance
                            page to see the corresponding action.
                        </li>
                    )}
                    {(rebalance?.actions || []).filter(a => a.research?.stale).length > 0 && (
                        <li>
                            Stale research on file (&gt; 30 days). Refresh those tickers
                            in Deep Research before acting on their recommendations.
                        </li>
                    )}
                    {(!decayedItems.length && (!rebalance || !rebalance.actions?.length)) && (
                        <li style={{ color: 'var(--text-muted)' }}>
                            Nothing pressing. Use this time to broaden coverage.
                        </li>
                    )}
                </ul>
            </div>
        </div>
    );
}

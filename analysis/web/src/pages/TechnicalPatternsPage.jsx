import { useCallback, useEffect, useMemo, useState } from 'react';
import { getAllPatterns, getPatternsByType, formatPercent } from '../utils/api';
import ResearchLink from '../components/ResearchLink';

const FILTERS = [
    { key: 'all', label: 'All' },
    { key: 'bullish', label: 'Bullish' },
    { key: 'bearish', label: 'Bearish' },
];

function confidenceLabel(confidence) {
    if (confidence >= 70) return 'Strong';
    if (confidence >= 50) return 'Moderate';
    return 'Weak';
}

function confidenceClass(confidence) {
    if (confidence >= 70) return 'pattern-confidence-high';
    if (confidence >= 50) return 'pattern-confidence-medium';
    return 'pattern-confidence-low';
}

function flattenPatterns(data) {
    if (!data?.pattern_types) return [];
    return Object.values(data.pattern_types)
        .flatMap(bucket => bucket.patterns || [])
        .sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
}

export default function TechnicalPatternsPage({ onSelectTicker, onRunResearch }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeFilter, setActiveFilter] = useState('all');
    const [universe, setUniverse] = useState('sp500');
    const [limit, setLimit] = useState(150);

    const load = useCallback(async (refresh = false, filter = 'all') => {
        setLoading(true);
        setError(null);
        try {
            const opts = { universe, limit, refresh };
            const next = filter && !FILTERS.some(f => f.key === filter)
                ? await getPatternsByType(filter, opts)
                : await getAllPatterns(opts);
            setData(next);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [universe, limit]);

    useEffect(() => {
        const id = window.setTimeout(() => load(false), 0);
        return () => window.clearTimeout(id);
    }, [load]);

    const patternTabs = useMemo(() => (
        Object.entries(data?.pattern_types || {}).map(([key, bucket]) => ({
            key,
            label: bucket.name,
            signal: bucket.signal,
            count: bucket.count || 0,
        }))
    ), [data]);

    const rows = useMemo(() => {
        const all = flattenPatterns(data);
        if (activeFilter === 'bullish') return all.filter(p => p.signal === 'bullish');
        if (activeFilter === 'bearish') return all.filter(p => p.signal === 'bearish');
        if (activeFilter === 'all') return all;
        return data?.pattern_types?.[activeFilter]?.patterns || [];
    }, [activeFilter, data]);

    const applyFilter = useCallback((filter) => {
        setActiveFilter(filter);
        if (!FILTERS.some(f => f.key === filter)) {
            load(false, filter);
        }
    }, [load]);

    return (
        <div className="fade-in patterns-page">
            <div className="page-header" style={{ flexWrap: 'wrap' }}>
                <div>
                    <h1 className="page-title">Technical Patterns</h1>
                    <p className="page-subtitle">
                        {data ? `${data.evaluated} tickers scanned · ${data.summary?.total_patterns || 0} patterns found` : 'Live chart-pattern scan'}
                    </p>
                </div>
                <div className="patterns-actions">
                    <select className="select" value={universe} onChange={e => setUniverse(e.target.value)} aria-label="Pattern universe">
                        <option value="sp500">S&P 500</option>
                        <option value="themes">Themes</option>
                        <option value="watchlist">Watchlist</option>
                    </select>
                    <input
                        className="input"
                        type="number"
                        min="1"
                        max="500"
                        value={limit}
                        onChange={e => setLimit(Number(e.target.value || 1))}
                        aria-label="Scan limit"
                    />
            <button className="btn btn-secondary" onClick={() => load(true, activeFilter)} disabled={loading}>
                        {loading ? <span className="spinner spinner-sm" /> : 'Refresh scan'}
                    </button>
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-md)' }}>{error}</div>}

            <div className="patterns-summary-grid">
                <div className="glass-card pattern-summary-card">
                    <span>Total</span>
                    <strong>{data?.summary?.total_patterns || 0}</strong>
                </div>
                <div className="glass-card pattern-summary-card bullish">
                    <span>Bullish</span>
                    <strong>{data?.summary?.bullish_patterns || 0}</strong>
                </div>
                <div className="glass-card pattern-summary-card bearish">
                    <span>Bearish</span>
                    <strong>{data?.summary?.bearish_patterns || 0}</strong>
                </div>
            </div>

            <div className="patterns-filter-strip">
                {FILTERS.map(filter => (
                    <button
                        key={filter.key}
                        className={`pattern-filter ${activeFilter === filter.key ? 'active' : ''}`}
                        onClick={() => applyFilter(filter.key)}
                    >
                        {filter.label}
                    </button>
                ))}
                {patternTabs.map(tab => (
                    <button
                        key={tab.key}
                        className={`pattern-filter ${tab.signal} ${activeFilter === tab.key ? 'active' : ''}`}
                        onClick={() => applyFilter(tab.key)}
                    >
                        {tab.label} <span>{tab.count}</span>
                    </button>
                ))}
            </div>

            <div className="glass-card patterns-results-card">
                {loading && (
                    <div className="loading-state" style={{ minHeight: 220 }}>
                        <div className="spinner" />
                        <span>Scanning pattern detectors...</span>
                    </div>
                )}
                {!loading && rows.length === 0 && (
                    <div className="empty-state">
                        <h3 style={{ color: 'var(--text-secondary)' }}>No patterns found</h3>
                        <p style={{ fontSize: '0.825rem' }}>Try a broader universe, higher scan limit, or a different pattern family.</p>
                    </div>
                )}
                {!loading && rows.length > 0 && (
                    <div className="table-container patterns-table-wrap">
                        <table className="patterns-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Ticker</th>
                                    <th>Company</th>
                                    <th>Pattern</th>
                                    <th>Signal</th>
                                    <th>Confidence</th>
                                    <th>Current</th>
                                    <th>Target</th>
                                    <th>Potential</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((pattern, idx) => {
                                    const potential = pattern.target_price && pattern.current_price
                                        ? ((pattern.target_price - pattern.current_price) / pattern.current_price) * 100
                                        : null;
                                    return (
                                        <tr
                                            key={`${pattern.ticker}-${pattern.pattern_type}-${idx}`}
                                            onClick={() => onSelectTicker?.(pattern.ticker)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <td>{idx + 1}</td>
                                            <td><span className="ticker-badge">{pattern.ticker}</span></td>
                                            <td>{pattern.company_name || 'N/A'}</td>
                                            <td>{pattern.pattern_name || pattern.name}</td>
                                            <td>
                                                <span className={`badge ${pattern.signal === 'bullish' ? 'badge-green' : 'badge-red'}`}>
                                                    {pattern.signal}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`pattern-confidence ${confidenceClass(pattern.confidence || 0)}`}>
                                                    {pattern.confidence || 0}% {confidenceLabel(pattern.confidence || 0)}
                                                </span>
                                            </td>
                                            <td>{pattern.current_price_fmt || 'N/A'}</td>
                                            <td>{pattern.target_price != null ? `$${Number(pattern.target_price).toFixed(2)}` : 'N/A'}</td>
                                            <td className={potential == null ? '' : potential >= 0 ? 'value-positive' : 'value-negative'}>
                                                {potential == null ? 'N/A' : formatPercent(potential, true)}
                                            </td>
                                            <td className="text-right">
                                                <ResearchLink ticker={pattern.ticker} onRunResearch={onRunResearch} />
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

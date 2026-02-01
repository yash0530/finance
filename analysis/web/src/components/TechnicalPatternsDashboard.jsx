import { useState, useEffect } from 'react';
import './TechnicalPatternsDashboard.css';

/**
 * TechnicalPatternsDashboard displays all detected chart patterns across S&P 500 stocks.
 * Fetches from /api/patterns/all endpoint and allows filtering by pattern type.
 */
function TechnicalPatternsDashboard({ onBack, onCompanySelect }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeFilter, setActiveFilter] = useState('all');

    useEffect(() => {
        async function loadPatterns() {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:5001/api/patterns/all');
                if (!response.ok) throw new Error('Failed to load pattern data');
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadPatterns();
    }, []);

    const getConfidenceClass = (confidence) => {
        if (confidence >= 70) return 'confidence-high';
        if (confidence >= 50) return 'confidence-medium';
        return 'confidence-low';
    };

    const getConfidenceLabel = (confidence) => {
        if (confidence >= 70) return 'Strong';
        if (confidence >= 50) return 'Moderate';
        return 'Weak';
    };

    const getSignalClass = (signal) => {
        return signal === 'bullish' ? 'signal-bullish' : 'signal-bearish';
    };

    const getSignalEmoji = (signal) => {
        return signal === 'bullish' ? '📈' : '📉';
    };

    // Get all patterns flat for the "all" view
    const getAllPatterns = () => {
        if (!data?.pattern_types) return [];
        const allPatterns = [];
        Object.entries(data.pattern_types).forEach(([, typeData]) => {
            allPatterns.push(...(typeData.patterns || []));
        });
        return allPatterns.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
    };

    // Get patterns for a specific filter
    const getFilteredPatterns = () => {
        if (!data?.pattern_types) return [];

        if (activeFilter === 'all') {
            return getAllPatterns();
        } else if (activeFilter === 'bullish') {
            return getAllPatterns().filter(p => p.signal === 'bullish');
        } else if (activeFilter === 'bearish') {
            return getAllPatterns().filter(p => p.signal === 'bearish');
        } else {
            return data.pattern_types[activeFilter]?.patterns || [];
        }
    };

    // Get pattern type tabs
    const getPatternTabs = () => {
        if (!data?.pattern_types) return [];
        return Object.entries(data.pattern_types).map(([key, typeData]) => ({
            key,
            name: typeData.name,
            signal: typeData.signal,
            count: typeData.count
        }));
    };

    if (loading) {
        return (
            <div className="patterns-dashboard">
                <div className="patterns-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="patterns-dashboard-loading">
                    <div className="spinner"></div>
                    <p>Scanning all stocks for technical patterns...</p>
                    <p className="loading-note">This may take a moment on first load.</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="patterns-dashboard">
                <div className="patterns-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="patterns-dashboard-error">
                    {error || 'Failed to load pattern data'}
                </div>
            </div>
        );
    }

    const patterns = getFilteredPatterns();
    const tabs = getPatternTabs();

    return (
        <div className="patterns-dashboard">
            <div className="patterns-dashboard-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="patterns-dashboard-title">
                    <h2>{data.title}</h2>
                    <p className="patterns-dashboard-desc">{data.description}</p>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="patterns-summary">
                <div className="summary-stat">
                    <span className="stat-value">{data.summary?.total_patterns || 0}</span>
                    <span className="stat-label">Total Patterns</span>
                </div>
                <div className="summary-stat bullish">
                    <span className="stat-value">{data.summary?.bullish_patterns || 0}</span>
                    <span className="stat-label">📈 Bullish</span>
                </div>
                <div className="summary-stat bearish">
                    <span className="stat-value">{data.summary?.bearish_patterns || 0}</span>
                    <span className="stat-label">📉 Bearish</span>
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="patterns-filters">
                <button
                    className={`filter-btn ${activeFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setActiveFilter('all')}
                >
                    All
                </button>
                <button
                    className={`filter-btn bullish ${activeFilter === 'bullish' ? 'active' : ''}`}
                    onClick={() => setActiveFilter('bullish')}
                >
                    📈 Bullish
                </button>
                <button
                    className={`filter-btn bearish ${activeFilter === 'bearish' ? 'active' : ''}`}
                    onClick={() => setActiveFilter('bearish')}
                >
                    📉 Bearish
                </button>
                <div className="filter-divider"></div>
                {tabs.map(tab => (
                    <button
                        key={tab.key}
                        className={`filter-btn pattern-type ${tab.signal} ${activeFilter === tab.key ? 'active' : ''}`}
                        onClick={() => setActiveFilter(tab.key)}
                    >
                        {tab.name} ({tab.count})
                    </button>
                ))}
            </div>

            {/* Patterns Table */}
            {patterns.length === 0 ? (
                <div className="patterns-no-data">
                    <div className="no-data-icon">🔍</div>
                    <h3>No Patterns Found</h3>
                    <p>No patterns match the current filter.</p>
                </div>
            ) : (
                <div className="patterns-table-container">
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
                            </tr>
                        </thead>
                        <tbody>
                            {patterns.map((pattern, idx) => {
                                const potential = pattern.target_price && pattern.current_price
                                    ? ((pattern.target_price - pattern.current_price) / pattern.current_price * 100).toFixed(1)
                                    : null;
                                return (
                                    <tr
                                        key={`${pattern.ticker}-${pattern.pattern_type}-${idx}`}
                                        className="clickable-row"
                                        onClick={() => onCompanySelect?.(pattern.ticker)}
                                    >
                                        <td className="rank-col">{idx + 1}</td>
                                        <td className="ticker-col">
                                            <span className="ticker-badge">{pattern.ticker}</span>
                                        </td>
                                        <td className="company-col">{pattern.company_name}</td>
                                        <td className="pattern-col">{pattern.pattern_name}</td>
                                        <td className="signal-col">
                                            <span className={`signal-badge ${getSignalClass(pattern.signal)}`}>
                                                {getSignalEmoji(pattern.signal)} {pattern.signal}
                                            </span>
                                        </td>
                                        <td className="confidence-col">
                                            <span className={`confidence-badge ${getConfidenceClass(pattern.confidence)}`}>
                                                {pattern.confidence}% ({getConfidenceLabel(pattern.confidence)})
                                            </span>
                                        </td>
                                        <td className="price-col">
                                            {pattern.current_price_fmt || `$${pattern.current_price}`}
                                        </td>
                                        <td className="price-col target-price">
                                            ${pattern.target_price}
                                        </td>
                                        <td className={`potential-col ${potential > 0 ? 'positive' : 'negative'}`}>
                                            {potential > 0 ? '+' : ''}{potential}%
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Info Panel */}
            <div className="patterns-info-panel">
                <h4>📘 About Technical Patterns</h4>
                <div className="patterns-info-grid">
                    <div className="info-section">
                        <h5>Reversal Patterns</h5>
                        <ul>
                            <li><strong>Head & Shoulders / Inverse:</strong> Classic reversal signals with ~83% accuracy</li>
                            <li><strong>Double/Triple Top:</strong> Bearish reversal after failed breakout attempts</li>
                            <li><strong>Double/Triple Bottom:</strong> Bullish reversal after multiple support tests</li>
                            <li><strong>Falling Wedge:</strong> Bullish reversal from converging downtrend</li>
                        </ul>
                    </div>
                    <div className="info-section">
                        <h5>Continuation Patterns</h5>
                        <ul>
                            <li><strong>Ascending Triangle:</strong> Bullish, flat resistance with rising support</li>
                            <li><strong>Descending Triangle:</strong> Bearish, flat support with falling resistance</li>
                            <li><strong>Cup and Handle:</strong> Bullish, U-shaped consolidation (~76% accuracy)</li>
                            <li><strong>Bullish Flag:</strong> Strong move followed by tight consolidation</li>
                        </ul>
                    </div>
                </div>
                <div className="patterns-legend">
                    <span className="legend-item"><span className="dot confidence-high"></span> Strong (≥70%)</span>
                    <span className="legend-item"><span className="dot confidence-medium"></span> Moderate (50-69%)</span>
                    <span className="legend-item"><span className="dot confidence-low"></span> Weak (&lt;50%)</span>
                </div>
            </div>
        </div>
    );
}

export default TechnicalPatternsDashboard;

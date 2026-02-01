import { useState, useEffect } from 'react';
import './HeadShouldersDashboard.css';

/**
 * HeadShouldersDashboard displays all stocks with detected Head & Shoulders patterns.
 * Fetches from /api/patterns/head-shoulders endpoint.
 */
function HeadShouldersDashboard({ onBack, onCompanySelect }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadPatterns() {
            try {
                setLoading(true);
                const response = await fetch('http://localhost:5001/api/patterns/head-shoulders');
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

    if (loading) {
        return (
            <div className="hs-dashboard">
                <div className="hs-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="hs-dashboard-loading">
                    <div className="spinner"></div>
                    <p>Scanning stocks for patterns... This may take a moment.</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="hs-dashboard">
                <div className="hs-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="hs-dashboard-error">
                    {error || 'Failed to load pattern data'}
                </div>
            </div>
        );
    }

    return (
        <div className="hs-dashboard">
            <div className="hs-dashboard-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="hs-dashboard-title">
                    <h2>{data.title}</h2>
                    <p className="hs-dashboard-desc">{data.description}</p>
                    <span className="hs-dashboard-count">{data.count} patterns detected</span>
                </div>
            </div>

            {data.count === 0 ? (
                <div className="hs-no-patterns">
                    <div className="hs-no-patterns-icon">📈</div>
                    <h3>No Patterns Detected</h3>
                    <p>No Head & Shoulders patterns were found in the current S&P 500 stocks.</p>
                    <p className="hs-note">Patterns are scanned using the last 6 months of price data.</p>
                </div>
            ) : (
                <div className="hs-dashboard-table-container">
                    <table className="hs-dashboard-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Sector</th>
                                <th>Confidence</th>
                                <th>Head Price</th>
                                <th>Neckline</th>
                                <th>Target</th>
                                <th>Current</th>
                                <th>vs Neckline</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.patterns.map((pattern, idx) => (
                                <tr
                                    key={pattern.ticker}
                                    className="clickable-row"
                                    onClick={() => onCompanySelect?.(pattern.ticker)}
                                >
                                    <td className="rank-col">{idx + 1}</td>
                                    <td className="ticker-col">
                                        <span className="ticker-badge">{pattern.ticker}</span>
                                    </td>
                                    <td className="company-col">{pattern.company_name}</td>
                                    <td className="sector-col">{pattern.sector}</td>
                                    <td className="confidence-col">
                                        <span className={`confidence-badge ${getConfidenceClass(pattern.confidence)}`}>
                                            {pattern.confidence}% ({getConfidenceLabel(pattern.confidence)})
                                        </span>
                                    </td>
                                    <td className="price-col">${pattern.head?.price}</td>
                                    <td className="price-col">${pattern.neckline}</td>
                                    <td className="price-col target-price">${pattern.target_price}</td>
                                    <td className="price-col">{pattern.current_price_fmt || `$${pattern.current_price}`}</td>
                                    <td className={`pct-col ${pattern.price_vs_neckline_pct > 0 ? 'above' : 'below'}`}>
                                        {pattern.price_vs_neckline_pct > 0 ? '+' : ''}{pattern.price_vs_neckline_pct}%
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="hs-info-panel">
                <h4>📘 What is a Head & Shoulders Pattern?</h4>
                <p>
                    A Head and Shoulders pattern is a chart formation that predicts a bearish reversal.
                    It consists of three peaks: a higher middle peak (head) between two lower peaks (shoulders).
                    When price breaks below the neckline, it often signals a potential decline to the target price.
                </p>
                <div className="hs-legend">
                    <span className="legend-item"><span className="dot confidence-high"></span> Strong (≥70%)</span>
                    <span className="legend-item"><span className="dot confidence-medium"></span> Moderate (50-69%)</span>
                    <span className="legend-item"><span className="dot confidence-low"></span> Weak (&lt;50%)</span>
                </div>
            </div>
        </div>
    );
}

export default HeadShouldersDashboard;

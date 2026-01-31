import { useState, useEffect } from 'react';
import './SpotlightDashboard.css';

/**
 * SpotlightDashboard displays ALL companies matching a spotlight category.
 * Fetches from /api/spotlight/<category> endpoint.
 */
function SpotlightDashboard({ category, onBack, onCompanySelect }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadCategory() {
            try {
                setLoading(true);
                const response = await fetch(`http://localhost:5001/api/spotlight/${category}`);
                if (!response.ok) throw new Error('Failed to load category data');
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadCategory();
    }, [category]);

    const formatMetric = (key, value) => {
        if (value === null || value === undefined) return 'N/A';
        if (key === 'revenue_growth' || key === 'year_change' || key === 'profit_margin' || key === 'dividend_yield') {
            return `${(value * 100).toFixed(1)}%`;
        }
        if (key === 'pe_ratio') {
            return `${value.toFixed(2)}x`;
        }
        if (key === 'forward_pe' || key === 'trailing_pe' || key === 'beta') {
            return value.toFixed(2);
        }
        return value;
    };

    const getColumnLabel = (key) => {
        const labels = {
            ticker: 'Ticker',
            company_name: 'Company',
            sector: 'Sector',
            revenue_growth: 'Rev Growth',
            year_change: '52W Change',
            profit_margin: 'Profit Mgn',
            pe_ratio: 'P/E Ratio',
            forward_pe: 'Fwd P/E',
            trailing_pe: 'Trail P/E',
            current_price_fmt: 'Price',
            dividend_yield: 'Div Yield',
            beta: 'Beta',
            market_cap_fmt: 'Mkt Cap'
        };
        return labels[key] || key;
    };

    if (loading) {
        return (
            <div className="spotlight-dashboard">
                <div className="spotlight-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="spotlight-dashboard-loading">Loading...</div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="spotlight-dashboard">
                <div className="spotlight-dashboard-header">
                    <button className="btn btn-secondary" onClick={onBack}>
                        ← Back to Dashboard
                    </button>
                </div>
                <div className="spotlight-dashboard-error">
                    {error || 'Failed to load category data'}
                </div>
            </div>
        );
    }

    // Determine which columns to show based on available data
    const columns = data.companies.length > 0
        ? Object.keys(data.companies[0]).filter(k => k !== 'market_cap')
        : [];

    return (
        <div className="spotlight-dashboard">
            <div className="spotlight-dashboard-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="spotlight-dashboard-title">
                    <h2>{data.title}</h2>
                    <p className="spotlight-dashboard-desc">{data.description}</p>
                    <span className="spotlight-dashboard-count">{data.count} companies</span>
                </div>
            </div>

            <div className="spotlight-dashboard-table-container">
                <table className="spotlight-dashboard-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            {columns.map(col => (
                                <th key={col}>{getColumnLabel(col)}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.companies.map((company, idx) => (
                            <tr
                                key={company.ticker}
                                className="clickable-row"
                                onClick={() => onCompanySelect?.(company.ticker)}
                            >
                                <td className="rank-col">{idx + 1}</td>
                                {columns.map(col => (
                                    <td
                                        key={col}
                                        className={col === 'ticker' ? 'ticker-col' : col === 'company_name' ? 'company-col' : 'metric-col'}
                                    >
                                        {col === 'ticker' ? (
                                            <span className="ticker-badge">{company[col]}</span>
                                        ) : col === 'current_price_fmt' || col === 'market_cap_fmt' ? (
                                            company[col]
                                        ) : (
                                            formatMetric(col, company[col])
                                        )}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default SpotlightDashboard;

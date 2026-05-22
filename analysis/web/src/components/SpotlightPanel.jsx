import { useState, useEffect } from 'react';
import './SpotlightPanel.css';

/**
 * SpotlightPanel displays spotlight company categories on the dashboard.
 * Each category card shows top 5 companies.
 * Clicking the card header opens the full category dashboard.
 * Clicking a company opens the company detail page.
 */
function SpotlightPanel({ onCompanySelect, onCategorySelect }) {
    const [spotlight, setSpotlight] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadSpotlight() {
            try {
                const response = await fetch('http://localhost:5001/api/spotlight');
                if (!response.ok) throw new Error('Failed to load spotlight');
                const data = await response.json();
                setSpotlight(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadSpotlight();
    }, []);

    if (loading) {
        return (
            <section className="spotlight-panel">
                <h2 className="section-title">✨ Spotlight Companies</h2>
                <div className="spotlight-loading">Loading spotlight...</div>
            </section>
        );
    }

    if (error || !spotlight) {
        return null; // Silently fail - don't break the dashboard
    }

    // Order for display - all 10 categories
    const categoryOrder = [
        'growth_stocks', 'hot_stocks', 'value_plays', 'momentum_leaders', 'quality_gems',
        'dividend_champions', 'low_volatility', 'mega_caps', 'turnaround_plays', 'high_beta_movers'
    ];

    const formatMetric = (key, value) => {
        if (value === null || value === undefined) return 'N/A';
        if (key === 'revenue_growth' || key === 'year_change' || key === 'profit_margin' || key === 'dividend_yield') {
            return `${(value * 100).toFixed(1)}%`;
        }
        if (key === 'pe_ratio') {
            return `${value.toFixed(2)}x`;
        }
        if (key === 'forward_pe' || key === 'trailing_pe' || key === 'beta') {
            return value.toFixed(1);
        }
        return value;
    };

    const getMetricLabel = (key) => {
        const labels = {
            revenue_growth: 'REV GROWTH',
            year_change: '52W CHANGE',
            profit_margin: 'PROFIT MGN',
            pe_ratio: 'P/E RATIO',
            forward_pe: 'FWD P/E',
            trailing_pe: 'TRAIL P/E',
            dividend_yield: 'DIV YIELD',
            beta: 'BETA',
            market_cap_fmt: 'MKT CAP'
        };
        return labels[key] || key;
    };

    const getCategoryColor = (key) => {
        const colors = {
            growth_stocks: '#10b981',
            hot_stocks: '#ef4444',
            value_plays: '#f59e0b',
            momentum_leaders: '#3b82f6',
            quality_gems: '#8b5cf6',
            dividend_champions: '#22c55e',
            low_volatility: '#64748b',
            mega_caps: '#0ea5e9',
            turnaround_plays: '#f97316',
            high_beta_movers: '#eab308'
        };
        return colors[key] || '#6b7280';
    };

    const getPrimaryMetric = (key) => {
        const metrics = {
            growth_stocks: 'revenue_growth',
            hot_stocks: 'year_change',
            value_plays: 'forward_pe',
            momentum_leaders: 'pe_ratio',
            quality_gems: 'profit_margin',
            dividend_champions: 'dividend_yield',
            low_volatility: 'beta',
            mega_caps: 'market_cap_fmt',
            turnaround_plays: 'year_change',
            high_beta_movers: 'beta'
        };
        return metrics[key];
    };

    return (
        <section className="spotlight-panel">
            <h2 className="section-title">✨ Spotlight Companies</h2>
            <p className="section-subtitle">Potential buy candidates based on fundamental analysis</p>

            <div className="spotlight-grid">
                {categoryOrder.map((key) => {
                    const category = spotlight[key];
                    if (!category || !category.companies?.length) return null;

                    const primaryMetric = getPrimaryMetric(key);
                    const accentColor = getCategoryColor(key);

                    return (
                        <div
                            key={key}
                            className="spotlight-card glass-card fade-in"
                            style={{ borderTopColor: accentColor }}
                        >
                            <div
                                className="spotlight-header clickable-header"
                                onClick={() => onCategorySelect?.(key)}
                                title="Click to see all matching companies"
                            >
                                <h3 className="spotlight-title">{category.title}</h3>
                                <span className="spotlight-expand-icon">→</span>
                            </div>
                            <p className="spotlight-description">{category.description}</p>

                            <div className="spotlight-companies">
                                {category.companies.map((company, i) => (
                                    <div
                                        key={company.ticker}
                                        className="spotlight-company clickable"
                                        onClick={() => onCompanySelect?.(company.ticker)}
                                    >
                                        <span className="spotlight-rank" style={{ color: accentColor }}>
                                            #{i + 1}
                                        </span>
                                        <div className="spotlight-company-info">
                                            <span className="spotlight-ticker font-mono">{company.ticker}</span>
                                            <span className="spotlight-name">{company.company_name}</span>
                                        </div>
                                        <div className="spotlight-metric">
                                            <span className="metric-value font-mono" style={{ color: accentColor }}>
                                                {formatMetric(primaryMetric, company[primaryMetric])}
                                            </span>
                                            <span className="metric-label">{getMetricLabel(primaryMetric)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}

export default SpotlightPanel;


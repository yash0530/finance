import './MetricsPanel.css';

function MetricsPanel({ stats, onCompanySelect }) {
    if (!stats) return null;

    const metrics = [
        {
            label: 'Total Companies',
            value: stats.total_companies,
            icon: '🏢'
        },
        {
            label: 'Total Market Cap',
            value: stats.total_market_cap_fmt,
            icon: '💰'
        },
        {
            label: 'Avg Forward P/E',
            value: stats.avg_forward_pe?.toFixed(2) || 'N/A',
            icon: '📊'
        },
        {
            label: 'Avg Profit Margin',
            value: stats.avg_profit_margin ? `${stats.avg_profit_margin.toFixed(1)}%` : 'N/A',
            icon: '📈'
        },
        {
            label: 'Sectors',
            value: stats.sector_count,
            icon: '🏭'
        },
        {
            label: 'Avg Revenue Growth',
            value: stats.avg_revenue_growth ? `${stats.avg_revenue_growth.toFixed(1)}%` : 'N/A',
            icon: '🚀'
        }
    ];

    return (
        <section className="metrics-panel">
            <div className="metrics-grid">
                {metrics.map((metric, index) => (
                    <div
                        key={metric.label}
                        className="metric-card glass-card fade-in"
                        style={{ animationDelay: `${index * 0.05}s` }}
                    >
                        <div className="metric-icon">{metric.icon}</div>
                        <div className="metric-content">
                            <span className="metric-value">{metric.value}</span>
                            <span className="metric-label">{metric.label}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Top Companies Section */}
            <div className="top-companies-section">
                <div className="top-list glass-card fade-in">
                    <h3>🏆 Top by Market Cap</h3>
                    <div className="top-items">
                        {stats.top_by_market_cap?.slice(0, 5).map((company, i) => (
                            <div
                                key={company.ticker}
                                className="top-item clickable"
                                onClick={() => onCompanySelect?.(company.ticker)}
                            >
                                <span className="rank">#{i + 1}</span>
                                <span className="ticker font-mono">{company.ticker}</span>
                                <span className="name">{company.company_name}</span>
                                <span className="value font-mono">{company.market_cap_fmt}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="top-list glass-card fade-in">
                    <h3>📉 Lowest Forward P/E</h3>
                    <div className="top-items">
                        {stats.lowest_forward_pe?.slice(0, 5).map((company, i) => (
                            <div
                                key={company.ticker}
                                className="top-item clickable"
                                onClick={() => onCompanySelect?.(company.ticker)}
                            >
                                <span className="rank">#{i + 1}</span>
                                <span className="ticker font-mono">{company.ticker}</span>
                                <span className="name">{company.company_name}</span>
                                <span className="value font-mono value-positive">
                                    {company.forward_pe?.toFixed(2)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="top-list glass-card fade-in">
                    <h3>🚀 Highest Growth</h3>
                    <div className="top-items">
                        {stats.highest_growth?.slice(0, 5).map((company, i) => (
                            <div
                                key={company.ticker}
                                className="top-item clickable"
                                onClick={() => onCompanySelect?.(company.ticker)}
                            >
                                <span className="rank">#{i + 1}</span>
                                <span className="ticker font-mono">{company.ticker}</span>
                                <span className="name">{company.company_name}</span>
                                <span className="value font-mono value-positive">
                                    {company.revenue_growth_fmt}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}

export default MetricsPanel;

import { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid, ReferenceLine } from 'recharts';
import { fetchCompanyByTicker, fetchStockHistory, fetchFinancials, getSectorColor, formatPercent, formatNumber } from '../utils/api';
import './CompanyDetail.css';

function CompanyDetail({ ticker, onBack }) {
    const [company, setCompany] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Stock history state - stores full 5Y data, filtered client-side
    const [historyData, setHistoryData] = useState(null);
    const [historyPeriod, setHistoryPeriod] = useState('1y');
    const [historyLoading, setHistoryLoading] = useState(false);

    // Financials state
    const [financials, setFinancials] = useState(null);

    // Refreshing state
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        async function loadCompany() {
            try {
                setLoading(true);
                setError(null);
                const data = await fetchCompanyByTicker(ticker);
                setCompany(data);
            } catch (err) {
                setError(err.message || 'Failed to load company');
            } finally {
                setLoading(false);
            }
        }
        loadCompany();
    }, [ticker]);

    // Load stock history ONCE on mount (5 years of data)
    useEffect(() => {
        async function loadHistory() {
            try {
                setHistoryLoading(true);
                const data = await fetchStockHistory(ticker, false);
                setHistoryData(data);
            } catch (err) {
                console.error('Failed to load stock history:', err);
            } finally {
                setHistoryLoading(false);
            }
        }
        loadHistory();
    }, [ticker]);

    // Load financials once per ticker
    useEffect(() => {
        async function loadFinancials() {
            try {
                const data = await fetchFinancials(ticker, false);
                setFinancials(data);
            } catch (err) {
                console.error('Failed to load financials:', err);
            }
        }
        loadFinancials();
    }, [ticker]);

    // Filter history data based on selected period (client-side)
    const filteredHistoryData = useMemo(() => {
        if (!historyData?.data) return [];

        const now = new Date();
        const cutoffDays = {
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '5y': 1825
        };

        const cutoff = new Date(now.getTime() - (cutoffDays[historyPeriod] * 24 * 60 * 60 * 1000));

        return historyData.data.filter(item => new Date(item.date) >= cutoff);
    }, [historyData, historyPeriod]);

    // Hard refresh function - bypasses cache
    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            const [histData, finData] = await Promise.all([
                fetchStockHistory(ticker, true),
                fetchFinancials(ticker, true)
            ]);
            setHistoryData(histData);
            setFinancials(finData);
        } catch (err) {
            console.error('Failed to refresh data:', err);
        } finally {
            setRefreshing(false);
        }
    };

    if (loading) {
        return (
            <div className="company-detail-loading">
                <div className="spinner"></div>
                <p>Loading company data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="company-detail-error">
                <p>⚠️ {error}</p>
                <button className="btn btn-secondary" onClick={onBack}>Back to Dashboard</button>
            </div>
        );
    }

    if (!company) return null;

    const sectorColor = getSectorColor(company.sector);
    const periods = [
        { value: '1mo', label: '1M' },
        { value: '3mo', label: '3M' },
        { value: '6mo', label: '6M' },
        { value: '1y', label: '1Y' },
        { value: '5y', label: '5Y' }
    ];

    // Custom tooltip for stock chart
    const StockTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="chart-tooltip">
                    <p className="tooltip-date">{label}</p>
                    <p className="tooltip-price">${payload[0].value.toFixed(2)}</p>
                </div>
            );
        }
        return null;
    };

    // Custom tooltip for financial charts
    const FinancialTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="chart-tooltip">
                    <p className="tooltip-date">{payload[0].payload.period}</p>
                    <p className="tooltip-price">{payload[0].payload.formatted}</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="company-detail">
            <div className="company-detail-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <button
                    className="btn btn-refresh"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    title="Fetch fresh data from API"
                >
                    {refreshing ? '⏳ Refreshing...' : '🔄 Refresh Data'}
                </button>
            </div>

            <div className="company-hero glass-card fade-in">
                <div className="hero-main">
                    <span className="hero-ticker" style={{ color: sectorColor }}>
                        {company.ticker}
                    </span>
                    <h1 className="hero-name">{company.company_name}</h1>
                    <div className="hero-tags">
                        <span className="tag sector-tag" style={{ background: sectorColor }}>
                            {company.sector}
                        </span>
                        <span className="tag industry-tag">{company.industry}</span>
                    </div>
                </div>
                <div className="hero-price">
                    <span className="current-price">{company.current_price_fmt}</span>
                    <span className={`year-change ${company.year_change >= 0 ? 'positive' : 'negative'}`}>
                        {company.year_change_fmt} YTD
                    </span>
                </div>
            </div>

            {/* Stock Price History Chart */}
            <div className="detail-section glass-card fade-in stock-chart-section">
                <div className="section-header-with-controls">
                    <h3 className="section-heading">📈 Stock Price History</h3>
                    <div className="period-selector">
                        {periods.map(p => (
                            <button
                                key={p.value}
                                className={`period-btn ${historyPeriod === p.value ? 'active' : ''}`}
                                onClick={() => setHistoryPeriod(p.value)}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>

                {historyData && (
                    <div className="price-range-info">
                        <span className="range-label">52-Week Range:</span>
                        <span className="range-low">${historyData.week_52_low?.toFixed(2) || 'N/A'}</span>
                        <div className="range-bar">
                            <div
                                className="range-current"
                                style={{
                                    left: historyData.week_52_low && historyData.week_52_high && company.current_price
                                        ? `${((company.current_price - historyData.week_52_low) / (historyData.week_52_high - historyData.week_52_low)) * 100}%`
                                        : '50%'
                                }}
                            />
                        </div>
                        <span className="range-high">${historyData.week_52_high?.toFixed(2) || 'N/A'}</span>
                    </div>
                )}

                <div className="stock-chart-container">
                    {historyLoading ? (
                        <div className="chart-loading">Loading chart data...</div>
                    ) : filteredHistoryData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={filteredHistoryData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={sectorColor} stopOpacity={0.3} />
                                        <stop offset="95%" stopColor={sectorColor} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="date"
                                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                                    tickFormatter={(date) => {
                                        const d = new Date(date);
                                        return historyPeriod === '5y'
                                            ? d.getFullYear().toString()
                                            : `${d.getMonth() + 1}/${d.getDate()}`;
                                    }}
                                    interval="preserveStartEnd"
                                    minTickGap={40}
                                />
                                <YAxis
                                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                                    tickFormatter={(val) => `$${val}`}
                                    domain={['auto', 'auto']}
                                    width={60}
                                />
                                <Tooltip content={<StockTooltip />} />
                                <Line
                                    type="monotone"
                                    dataKey="close"
                                    stroke={sectorColor}
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 4, fill: sectorColor }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="chart-loading">No historical data available</div>
                    )}
                </div>
            </div>

            <div className="detail-grid">
                {/* Market Data Section */}
                <div className="detail-section glass-card fade-in">
                    <h3 className="section-heading">📊 Market Data</h3>
                    <div className="metrics-list">
                        <div className="metric-row">
                            <span className="metric-name">Market Cap</span>
                            <span className="metric-value">{company.market_cap_fmt}</span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Current Price</span>
                            <span className="metric-value">{company.current_price_fmt}</span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">52-Week Change</span>
                            <span className={`metric-value ${company.year_change >= 0 ? 'positive' : 'negative'}`}>
                                {company.year_change_fmt}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Beta</span>
                            <span className="metric-value">
                                {company.beta != null ? formatNumber(company.beta) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Dividend Yield</span>
                            <span className="metric-value">{company.dividend_yield_fmt}</span>
                        </div>
                    </div>
                </div>

                {/* Valuation Section */}
                <div className="detail-section glass-card fade-in">
                    <h3 className="section-heading">💰 Valuation</h3>
                    <div className="metrics-list">
                        <div className="metric-row">
                            <span className="metric-name">Forward P/E</span>
                            <span className="metric-value">
                                {company.forward_pe != null ? formatNumber(company.forward_pe) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Trailing P/E</span>
                            <span className="metric-value">
                                {company.trailing_pe != null ? formatNumber(company.trailing_pe) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">P/E Ratio</span>
                            <span className="metric-value">{company.pe_ratio_fmt}</span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Price to Sales</span>
                            <span className="metric-value">
                                {company.price_to_sales != null ? formatNumber(company.price_to_sales) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Price to Book</span>
                            <span className="metric-value">
                                {company.price_to_book != null ? formatNumber(company.price_to_book) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">EV/Revenue</span>
                            <span className="metric-value">
                                {company.ev_to_revenue != null ? formatNumber(company.ev_to_revenue) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">EV/EBITDA</span>
                            <span className="metric-value">
                                {company.ev_to_ebitda != null ? formatNumber(company.ev_to_ebitda) : 'N/A'}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">EPS (TTM)</span>
                            <span className="metric-value">
                                {company.eps != null ? `$${formatNumber(company.eps)}` : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Revenue & Income Section - Enhanced with time period labels */}
                <div className="detail-section glass-card fade-in">
                    <h3 className="section-heading">💵 Revenue & Income</h3>
                    <div className="metrics-list">
                        <div className="metric-row">
                            <span className="metric-name">Total Revenue <span className="metric-period">(TTM)</span></span>
                            <span className="metric-value">{company.total_revenue_fmt}</span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Net Income <span className="metric-period">(TTM)</span></span>
                            <span className="metric-value">{company.net_income_fmt}</span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Revenue Growth <span className="metric-period">(YoY)</span></span>
                            <span className={`metric-value ${company.revenue_growth >= 0 ? 'positive' : 'negative'}`}>
                                {company.revenue_growth_fmt}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Profitability Section */}
                <div className="detail-section glass-card fade-in">
                    <h3 className="section-heading">🎯 Profitability</h3>
                    <div className="metrics-list">
                        <div className="metric-row">
                            <span className="metric-name">Profit Margin</span>
                            <span className={`metric-value ${company.profit_margin >= 0 ? 'positive' : 'negative'}`}>
                                {company.profit_margin_fmt}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Operating Margin</span>
                            <span className={`metric-value ${company.operating_margin >= 0 ? 'positive' : 'negative'}`}>
                                {company.operating_margin_fmt}
                            </span>
                        </div>
                        <div className="metric-row">
                            <span className="metric-name">Gross Margin</span>
                            <span className="metric-value">
                                {company.gross_margin != null ? formatPercent(company.gross_margin) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Quarterly Financials Charts */}
            {financials && (financials.quarterly_revenue?.length > 0 || financials.quarterly_earnings?.length > 0) && (
                <div className="financials-section">
                    <h2 className="financials-title">📊 Quarterly Financials</h2>
                    <div className="financials-grid">
                        {financials.quarterly_revenue?.length > 0 && (
                            <div className="detail-section glass-card fade-in chart-card">
                                <h3 className="section-heading">Revenue by Quarter</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={financials.quarterly_revenue} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis
                                            dataKey="period"
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            angle={-45}
                                            textAnchor="end"
                                            height={50}
                                        />
                                        <YAxis
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            tickFormatter={(val) => `$${(val / 1e9).toFixed(0)}B`}
                                            width={50}
                                        />
                                        <Tooltip content={<FinancialTooltip />} />
                                        <Bar dataKey="value" fill={sectorColor} radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )}

                        {financials.quarterly_earnings?.length > 0 && (
                            <div className="detail-section glass-card fade-in chart-card">
                                <h3 className="section-heading">Net Income by Quarter</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={financials.quarterly_earnings} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis
                                            dataKey="period"
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            angle={-45}
                                            textAnchor="end"
                                            height={50}
                                        />
                                        <YAxis
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            tickFormatter={(val) => `$${(val / 1e9).toFixed(0)}B`}
                                            width={50}
                                        />
                                        <Tooltip content={<FinancialTooltip />} />
                                        <ReferenceLine y={0} stroke="#6b7280" />
                                        <Bar
                                            dataKey="value"
                                            fill="#10b981"
                                            radius={[4, 4, 0, 0]}
                                        />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Annual Financials */}
            {financials && (financials.annual_revenue?.length > 0) && (
                <div className="financials-section">
                    <h2 className="financials-title">📅 Annual Financials</h2>
                    <div className="financials-grid">
                        {financials.annual_revenue?.length > 0 && (
                            <div className="detail-section glass-card fade-in chart-card">
                                <h3 className="section-heading">Annual Revenue Trend</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={financials.annual_revenue} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis
                                            dataKey="period"
                                            tick={{ fill: '#9ca3af', fontSize: 11 }}
                                        />
                                        <YAxis
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            tickFormatter={(val) => `$${(val / 1e9).toFixed(0)}B`}
                                            width={50}
                                        />
                                        <Tooltip content={<FinancialTooltip />} />
                                        <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )}

                        {financials.annual_earnings?.length > 0 && (
                            <div className="detail-section glass-card fade-in chart-card">
                                <h3 className="section-heading">Annual Net Income Trend</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={financials.annual_earnings} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis
                                            dataKey="period"
                                            tick={{ fill: '#9ca3af', fontSize: 11 }}
                                        />
                                        <YAxis
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            tickFormatter={(val) => `$${(val / 1e9).toFixed(0)}B`}
                                            width={50}
                                        />
                                        <Tooltip content={<FinancialTooltip />} />
                                        <ReferenceLine y={0} stroke="#6b7280" />
                                        <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default CompanyDetail;

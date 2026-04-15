import { useState, useEffect, useMemo } from 'react';
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
    const [sortField, setSortField] = useState(null);
    const [sortOrder, setSortOrder] = useState('asc');
    
    // Smart Filters
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState({
        confidenceMin: '',
        confidenceMax: '',
        potentialMin: '',
        potentialMin: '',
        potentialMax: '',
        peRatioMin: '',
        peRatioMax: '',
        forwardPeMin: '',
        forwardPeMax: '',
        trailingPeMin: '',
        trailingPeMax: '',
        marketCapMin: '',
        marketCapMax: '',
        profitMarginMin: '',
        profitMarginMax: '',
        revenueGrowthMin: '',
        revenueGrowthMax: '',
        yearChangeMin: '',
        yearChangeMax: '',
        epsMin: '',
        epsMax: '',
        betaMin: '',
        betaMax: '',
        fiftyTwoWeekHighMin: '',
        fiftyTwoWeekHighMax: '',
        fiftyTwoWeekLowMin: '',
        fiftyTwoWeekLowMax: '',
        dividendYieldMin: '',
        dividendYieldMax: '',
        dayChangePercentMin: '',
        dayChangePercentMax: '',
    });

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

    const handleSort = (field) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
    };

    const handleFilterChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({ ...prev, [name]: value }));
    };

    const clearFilters = () => {
        setFilters({
            confidenceMin: '',
            confidenceMax: '',
            potentialMin: '',
            potentialMin: '',
            potentialMax: '',
            peRatioMin: '',
            peRatioMax: '',
            forwardPeMin: '',
            forwardPeMax: '',
            trailingPeMin: '',
            trailingPeMax: '',
            marketCapMin: '',
            marketCapMax: '',
            profitMarginMin: '',
            profitMarginMax: '',
            revenueGrowthMin: '',
            revenueGrowthMax: '',
            yearChangeMin: '',
            yearChangeMax: '',
            epsMin: '',
            epsMax: '',
            betaMin: '',
            betaMax: '',
            fiftyTwoWeekHighMin: '',
            fiftyTwoWeekHighMax: '',
            fiftyTwoWeekLowMin: '',
            fiftyTwoWeekLowMax: '',
            dividendYieldMin: '',
            dividendYieldMax: '',
            dayChangePercentMin: '',
            dayChangePercentMax: '',
        });
    };

    const hasActiveFilters = Object.values(filters).some(v => v !== '');

    const basePatterns = getFilteredPatterns();

    const filteredAndSortedData = useMemo(() => {
        let processed = [...basePatterns];

        // Apply filters
        const applyMinMax = (prop, min, max) => {
            if (min || max) {
                processed = processed.filter(p => {
                    let val = p[prop];
                    if (val === null || val === undefined || isNaN(val)) return false;
                    
                    if (min && val < parseFloat(min)) return false;
                    if (max && val > parseFloat(max)) return false;
                    return true;
                });
            }
        };

        applyMinMax('confidence', filters.confidenceMin, filters.confidenceMax);

        if (filters.potentialMin || filters.potentialMax) {
            processed = processed.filter(p => {
                const potential = p.target_price && p.current_price 
                    ? ((p.target_price - p.current_price) / p.current_price * 100) 
                    : null;
                
                if (potential === null || isNaN(potential)) return false;
                if (filters.potentialMin && potential < parseFloat(filters.potentialMin)) return false;
                if (filters.potentialMax && potential > parseFloat(filters.potentialMax)) return false;
                return true;
            });
        }

        applyMinMax('pe_ratio', filters.peRatioMin, filters.peRatioMax);
        applyMinMax('forward_pe', filters.forwardPeMin, filters.forwardPeMax);
        applyMinMax('trailing_pe', filters.trailingPeMin, filters.trailingPeMax);
        applyMinMax('profit_margin', filters.profitMarginMin, filters.profitMarginMax, true);
        applyMinMax('revenue_growth', filters.revenueGrowthMin, filters.revenueGrowthMax, true);
        applyMinMax('year_change', filters.yearChangeMin, filters.yearChangeMax, true);
        applyMinMax('eps', filters.epsMin, filters.epsMax);
        applyMinMax('beta', filters.betaMin, filters.betaMax);
        applyMinMax('fifty_two_week_high', filters.fiftyTwoWeekHighMin, filters.fiftyTwoWeekHighMax);
        applyMinMax('fifty_two_week_low', filters.fiftyTwoWeekLowMin, filters.fiftyTwoWeekLowMax);
        applyMinMax('dividend_yield', filters.dividendYieldMin, filters.dividendYieldMax, true);
        applyMinMax('day_change_percent', filters.dayChangePercentMin, filters.dayChangePercentMax);

        // Market Cap filter (in billions)
        if (filters.marketCapMin || filters.marketCapMax) {
            processed = processed.filter(c => {
                const cap = parseFloat(c.market_cap);
                if (isNaN(cap)) return false;
                const capBillions = cap / 1e9;
                if (filters.marketCapMin && capBillions < parseFloat(filters.marketCapMin)) return false;
                if (filters.marketCapMax && capBillions > parseFloat(filters.marketCapMax)) return false;
                return true;
            });
        }

        // Apply sort
        if (sortField) {
            processed.sort((a, b) => {
                let aVal = a[sortField];
                let bVal = b[sortField];

                if (sortField === 'potential') {
                    const getPot = p => p.target_price && p.current_price ? (p.target_price - p.current_price) / p.current_price : null;
                    aVal = getPot(a);
                    bVal = getPot(b);
                }
                
                if (aVal === null || aVal === undefined) return 1;
                if (bVal === null || bVal === undefined) return -1;

                if (typeof aVal === 'string' && typeof bVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }

                if (sortOrder === 'asc') {
                    return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
                } else {
                    return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
                }
            });
        }

        return processed;
    }, [basePatterns, filters, sortField, sortOrder]);

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon active">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
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

    const tabs = getPatternTabs();
    
    const columns = [
        { key: 'ticker', label: 'Ticker' },
        { key: 'company_name', label: 'Company' },
        { key: 'pattern_name', label: 'Pattern' },
        { key: 'signal', label: 'Signal' },
        { key: 'confidence', label: 'Confidence' },
        { key: 'current_price', label: 'Current' },
        { key: 'target_price', label: 'Target' },
        { key: 'potential', label: 'Potential' },
        { key: 'market_cap', label: 'Market Cap' },
        { key: 'pe_ratio', label: 'P/E Ratio' },
        { key: 'forward_pe', label: 'Fwd P/E' },
        { key: 'trailing_pe', label: 'Trail P/E' },
        { key: 'profit_margin', label: 'Margin' },
        { key: 'revenue_growth', label: 'Rev Growth' },
        { key: 'year_change', label: '52W Change' },
        { key: 'beta', label: 'Beta' },
        { key: 'eps', label: 'EPS' },
        { key: 'dividend_yield', label: 'Div Yield' },
        { key: 'fifty_two_week_high', label: '52W High' },
        { key: 'fifty_two_week_low', label: '52W Low' },
        { key: 'day_change_percent', label: 'Day Chg' }
    ];

    return (
        <div className="patterns-dashboard">
            <div className="patterns-dashboard-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="patterns-dashboard-title">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <h2>{data.title}</h2>
                        <button
                            className={`btn btn-filter ${showFilters ? 'active' : ''}`}
                            onClick={() => setShowFilters(!showFilters)}
                            style={{ padding: '0.4rem 0.8rem', fontSize: '13px' }}
                        >
                            🔍 {showFilters ? 'Hide Filters' : 'Show Filters'}
                        </button>
                    </div>
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

            {showFilters && (
                <div className="filter-panel fade-in" style={{ marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '1.5rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Confidence Score</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="confidenceMin" placeholder="Min" value={filters.confidenceMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="confidenceMax" placeholder="Max" value={filters.confidenceMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Target Potential (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="potentialMin" placeholder="Min" value={filters.potentialMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="potentialMax" placeholder="Max" value={filters.potentialMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>P/E Ratio</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="peRatioMin" placeholder="Min" value={filters.peRatioMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="peRatioMax" placeholder="Max" value={filters.peRatioMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Forward P/E</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="forwardPeMin" placeholder="Min" value={filters.forwardPeMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="forwardPeMax" placeholder="Max" value={filters.forwardPeMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Trailing P/E</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="trailingPeMin" placeholder="Min" value={filters.trailingPeMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="trailingPeMax" placeholder="Max" value={filters.trailingPeMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Market Cap (Billion $)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="marketCapMin" placeholder="Min" value={filters.marketCapMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="marketCapMax" placeholder="Max" value={filters.marketCapMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Profit Margin (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="profitMarginMin" placeholder="Min" value={filters.profitMarginMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="profitMarginMax" placeholder="Max" value={filters.profitMarginMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Revenue Growth (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="revenueGrowthMin" placeholder="Min" value={filters.revenueGrowthMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="revenueGrowthMax" placeholder="Max" value={filters.revenueGrowthMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>52W Change (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="yearChangeMin" placeholder="Min" value={filters.yearChangeMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="yearChangeMax" placeholder="Max" value={filters.yearChangeMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Beta</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" step="0.1" name="betaMin" placeholder="Min" value={filters.betaMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" step="0.1" name="betaMax" placeholder="Max" value={filters.betaMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>EPS ($)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" step="0.01" name="epsMin" placeholder="Min" value={filters.epsMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" step="0.01" name="epsMax" placeholder="Max" value={filters.epsMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Div Yield (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" step="0.1" name="dividendYieldMin" placeholder="Min" value={filters.dividendYieldMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" step="0.1" name="dividendYieldMax" placeholder="Max" value={filters.dividendYieldMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>52W High ($)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="fiftyTwoWeekHighMin" placeholder="Min" value={filters.fiftyTwoWeekHighMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="fiftyTwoWeekHighMax" placeholder="Max" value={filters.fiftyTwoWeekHighMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>52W Low ($)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="fiftyTwoWeekLowMin" placeholder="Min" value={filters.fiftyTwoWeekLowMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="fiftyTwoWeekLowMax" placeholder="Max" value={filters.fiftyTwoWeekLowMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Day Change (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" step="0.1" name="dayChangePercentMin" placeholder="Min" value={filters.dayChangePercentMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" step="0.1" name="dayChangePercentMax" placeholder="Max" value={filters.dayChangePercentMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    {hasActiveFilters && (
                        <div className="filter-actions" style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
                            <button className="btn btn-clear" onClick={clearFilters} style={{ background: 'transparent', color: 'var(--text-muted)', border: 'none', padding: '0.5rem 1rem', cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                ✕ Clear All Filters
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Patterns Table */}
            {filteredAndSortedData.length === 0 ? (
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
                                {columns.map(col => (
                                    <th key={col.key} onClick={() => handleSort(col.key)} className="clickable-header">
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', whiteSpace: 'nowrap' }}>
                                            <span>{col.label}</span> <SortIcon field={col.key} />
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filteredAndSortedData.map((pattern, idx) => {
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
                                        <td className="price-col font-mono">
                                            {pattern.current_price_fmt || `$${pattern.current_price}`}
                                        </td>
                                        <td className="price-col target-price font-mono">
                                            ${pattern.target_price}
                                        </td>
                                        <td className={`potential-col font-mono ${potential > 0 ? 'positive' : 'negative'}`}>
                                            {potential > 0 ? '+' : ''}{potential}%
                                        </td>
                                        <td className="price-col font-mono">{pattern.market_cap_fmt}</td>
                                        <td className="price-col font-mono">{pattern.pe_ratio != null ? pattern.pe_ratio.toFixed(2) : '-'}</td>
                                        <td className="price-col font-mono">{pattern.forward_pe != null ? pattern.forward_pe.toFixed(2) : '-'}</td>
                                        <td className="price-col font-mono">{pattern.trailing_pe != null ? pattern.trailing_pe.toFixed(2) : '-'}</td>
                                        <td className="price-col font-mono">{pattern.profit_margin_fmt || '-'}</td>
                                        <td className="price-col font-mono">{pattern.revenue_growth_fmt || '-'}</td>
                                        <td className="price-col font-mono">{pattern.year_change_fmt || '-'}</td>
                                        <td className="price-col font-mono">{pattern.beta != null ? pattern.beta.toFixed(2) : '-'}</td>
                                        <td className="price-col font-mono">{pattern.eps != null ? `$${pattern.eps.toFixed(2)}` : '-'}</td>
                                        <td className="price-col font-mono">{pattern.dividend_yield_fmt || '-'}</td>
                                        <td className="price-col font-mono">{pattern.fifty_two_week_high != null ? `$${pattern.fifty_two_week_high.toFixed(2)}` : '-'}</td>
                                        <td className="price-col font-mono">{pattern.fifty_two_week_low != null ? `$${pattern.fifty_two_week_low.toFixed(2)}` : '-'}</td>
                                        <td className={`pct-col font-mono ${pattern.day_change_percent > 0 ? 'above' : 'below'}`}>
                                            {pattern.day_change_percent != null ? `${pattern.day_change_percent > 0 ? '+' : ''}${(pattern.day_change_percent * 100).toFixed(2)}%` : '-'}
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

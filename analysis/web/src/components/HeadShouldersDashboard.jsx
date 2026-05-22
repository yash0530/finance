import { useState, useEffect, useMemo } from 'react';
import './HeadShouldersDashboard.css';

/**
 * HeadShouldersDashboard displays all stocks with detected Head & Shoulders patterns.
 * Fetches from /api/patterns/head-shoulders endpoint.
 */
function HeadShouldersDashboard({ onBack, onCompanySelect }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sortField, setSortField] = useState(null);
    const [sortOrder, setSortOrder] = useState('asc');
    
    // Smart Filters
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState({
        sector: '',
        confidenceMin: '',
        confidenceMax: '',
        priceVsNeckMin: '',
        priceVsNeckMax: '',
        targetPotentialMin: '',
        targetPotentialMin: '',
        targetPotentialMax: '',
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
            sector: '',
            confidenceMin: '',
            confidenceMax: '',
            priceVsNeckMin: '',
            priceVsNeckMax: '',
            targetPotentialMin: '',
            targetPotentialMin: '',
            targetPotentialMax: '',
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

    const sectors = useMemo(() => {
        if (!data || !data.patterns) return [];
        const uniqueSectors = [...new Set(data.patterns.map(p => p.sector).filter(Boolean))];
        return uniqueSectors.sort();
    }, [data]);

    const filteredAndSortedData = useMemo(() => {
        if (!data || !data.patterns) return [];
        
        let processed = [...data.patterns];

        // Apply filters
        if (filters.sector) {
            processed = processed.filter(p => p.sector === filters.sector);
        }

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
        applyMinMax('price_vs_neckline_pct', filters.priceVsNeckMin, filters.priceVsNeckMax);

        if (filters.targetPotentialMin || filters.targetPotentialMax) {
            processed = processed.filter(p => {
                const potential = p.target_price && p.current_price 
                    ? ((p.target_price - p.current_price) / p.current_price * 100) 
                    : null;
                
                if (potential === null || isNaN(potential)) return false;
                if (filters.targetPotentialMin && potential < parseFloat(filters.targetPotentialMin)) return false;
                if (filters.targetPotentialMax && potential > parseFloat(filters.targetPotentialMax)) return false;
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

                if (sortField === 'head_price') {
                    aVal = a.head?.price;
                    bVal = b.head?.price;
                } else if (sortField === 'current_price') {
                    aVal = a.current_price;
                    bVal = b.current_price;
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
    }, [data, filters, sortField, sortOrder]);

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon active">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
    };


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

    const columns = [
        { key: 'ticker', label: 'Ticker' },
        { key: 'company_name', label: 'Company' },
        { key: 'sector', label: 'Sector' },
        { key: 'confidence', label: 'Confidence' },
        { key: 'head_price', label: 'Head Price' },
        { key: 'neckline', label: 'Neckline' },
        { key: 'target_price', label: 'Target' },
        { key: 'current_price', label: 'Current' },
        { key: 'price_vs_neckline_pct', label: 'vs Neckline' },
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
        <div className="hs-dashboard">
            <div className="hs-dashboard-header">
                <button className="btn btn-secondary" onClick={onBack}>
                    ← Back to Dashboard
                </button>
                <div className="hs-dashboard-title">
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
                    <p className="hs-dashboard-desc">{data.description}</p>
                    <span className="hs-dashboard-count">{filteredAndSortedData.length} patterns {hasActiveFilters && `(filtered from ${data.count})`}</span>
                </div>
            </div>

            {showFilters && (
                <div className="filter-panel fade-in" style={{ marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '1.5rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Sector</label>
                            <select name="sector" value={filters.sector} onChange={handleFilterChange} style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }}>
                                <option value="">All Sectors</option>
                                {sectors.map(s => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </select>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Confidence Score</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="confidenceMin" placeholder="Min" value={filters.confidenceMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="confidenceMax" placeholder="Max" value={filters.confidenceMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Price vs Neckline (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="priceVsNeckMin" placeholder="Min" value={filters.priceVsNeckMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="priceVsNeckMax" placeholder="Max" value={filters.priceVsNeckMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Target Potential (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="targetPotentialMin" placeholder="Min" value={filters.targetPotentialMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="targetPotentialMax" placeholder="Max" value={filters.targetPotentialMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
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
                            {filteredAndSortedData.map((pattern, idx) => (
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
                                    <td className="price-col font-mono">${pattern.head?.price}</td>
                                    <td className="price-col font-mono">${pattern.neckline}</td>
                                    <td className="price-col target-price font-mono">${pattern.target_price}</td>
                                    <td className="price-col font-mono">{pattern.current_price_fmt || `$${pattern.current_price}`}</td>
                                    <td className={`pct-col font-mono ${pattern.price_vs_neckline_pct > 0 ? 'above' : 'below'}`}>
                                        {pattern.price_vs_neckline_pct > 0 ? '+' : ''}{pattern.price_vs_neckline_pct}%
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

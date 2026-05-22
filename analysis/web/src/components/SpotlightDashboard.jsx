import { useState, useEffect, useMemo } from 'react';
import './SpotlightDashboard.css';

/**
 * SpotlightDashboard displays ALL companies matching a spotlight category.
 * Fetches from /api/spotlight/<category> endpoint.
 */
function SpotlightDashboard({ category, onBack, onCompanySelect }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sortField, setSortField] = useState(null);
    const [sortOrder, setSortOrder] = useState('asc');
    
    // Smart Filters
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState({
        sector: '',
        peRatioMin: '',
        peRatioMax: '',
        profitMarginMin: '',
        profitMarginMax: '',
        revenueGrowthMin: '',
        revenueGrowthMax: '',
        yearChangeMin: '',
        yearChangeMax: '',
        marketCapMin: '',
        marketCapMax: '',
        forwardPeMin: '',
        forwardPeMax: '',
        trailingPeMin: '',
        trailingPeMax: '',
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
            peRatioMin: '',
            peRatioMax: '',
            profitMarginMin: '',
            profitMarginMax: '',
            revenueGrowthMin: '',
            revenueGrowthMax: '',
            yearChangeMin: '',
            yearChangeMax: '',
            marketCapMin: '',
            marketCapMax: '',
            forwardPeMin: '',
            forwardPeMax: '',
            trailingPeMin: '',
            trailingPeMax: '',
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
        if (!data || !data.companies) return [];
        const uniqueSectors = [...new Set(data.companies.map(c => c.sector).filter(Boolean))];
        return uniqueSectors.sort();
    }, [data]);

    const filteredAndSortedData = useMemo(() => {
        if (!data || !data.companies) return [];
        
        let processed = [...data.companies];

        // Apply filters
        if (filters.sector) {
            processed = processed.filter(c => c.sector === filters.sector);
        }

        const applyMinMax = (prop, min, max, isPercentage = false) => {
            if (min || max) {
                processed = processed.filter(c => {
                    let val = c[prop];
                    if (val === null || val === undefined || isNaN(val)) return false;
                    
                    if (isPercentage) val = val * 100;

                    if (min && val < parseFloat(min)) return false;
                    if (max && val > parseFloat(max)) return false;
                    return true;
                });
            }
        };

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

                if (aVal === null || aVal === undefined) return 1;
                if (bVal === null || bVal === undefined) return -1;

                if (typeof aVal === 'string' && aVal.startsWith('$')) {
                    const parseVal = (v) => {
                        let numStr = v.replace(/[\$,]/g, '');
                        let multiplier = 1;
                        if (numStr.endsWith('T')) { multiplier = 1e12; numStr = numStr.slice(0, -1); }
                        else if (numStr.endsWith('B')) { multiplier = 1e9; numStr = numStr.slice(0, -1); }
                        else if (numStr.endsWith('M')) { multiplier = 1e6; numStr = numStr.slice(0, -1); }
                        return parseFloat(numStr) * multiplier;
                    };
                    aVal = parseVal(aVal);
                    bVal = parseVal(bVal);
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
                    <p className="spotlight-dashboard-desc">{data.description}</p>
                    <span className="spotlight-dashboard-count">{filteredAndSortedData.length} companies {hasActiveFilters && `(filtered from ${data.companies.length})`}</span>
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
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>P/E Ratio</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="peRatioMin" placeholder="Min" value={filters.peRatioMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="peRatioMax" placeholder="Max" value={filters.peRatioMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Profit Margin (%)</label>
                            <div className="range-inputs" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input type="number" name="profitMarginMin" placeholder="Min" value={filters.profitMarginMin} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>to</span>
                                <input type="number" name="profitMarginMax" placeholder="Max" value={filters.profitMarginMax} onChange={handleFilterChange} style={{ width: '80px', padding: '0.6rem', borderRadius: '6px', background: 'var(--bg-darker)', border: '1px solid var(--border-color)', color: 'var(--text-light)', outline: 'none' }} />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
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

            <div className="spotlight-dashboard-table-container">
                <table className="spotlight-dashboard-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            {columns.map(col => (
                                <th key={col} onClick={() => handleSort(col)} className="clickable-header">
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <span>{getColumnLabel(col)}</span> <SortIcon field={col} />
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {filteredAndSortedData.map((company, idx) => (
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

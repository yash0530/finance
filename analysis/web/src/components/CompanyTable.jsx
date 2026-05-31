import { useState, useEffect, useMemo } from 'react';
import { fetchCompaniesBySector, fetchCompanies, getSectorColor, formatNumber } from '../utils/api';
import ResearchLink from './ResearchLink';
import './CompanyTable.css';

function CompanyTable({ sector, searchResults, showAll, onCompanySelect, onRunResearch }) {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortField, setSortField] = useState('forward_pe');
    const [sortOrder, setSortOrder] = useState('asc');

    // Filter state
    const [filters, setFilters] = useState({
        sector: '',
        forwardPeMin: '',
        forwardPeMax: '',
        trailingPeMin: '',
        trailingPeMax: '',
        peRatioMin: '',
        peRatioMax: '',
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
    const [showFilters, setShowFilters] = useState(false);

    useEffect(() => {
        async function loadCompanies() {
            if (searchResults) {
                setCompanies(searchResults);
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                let data;
                if (showAll) {
                    const response = await fetchCompanies();
                    data = response.data;
                } else if (sector) {
                    const response = await fetchCompaniesBySector(sector);
                    data = response.data;
                } else {
                    setLoading(false);
                    return;
                }
                setCompanies(data);
            } catch (err) {
                console.error('Failed to load companies:', err);
            } finally {
                setLoading(false);
            }
        }

        loadCompanies();
    }, [sector, searchResults, showAll]);

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
            forwardPeMin: '',
            forwardPeMax: '',
            trailingPeMin: '',
            trailingPeMax: '',
            peRatioMin: '',
            peRatioMax: '',
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

    // Get unique sectors for dropdown
    const sectors = useMemo(() => {
        const uniqueSectors = [...new Set(companies.map(c => c.sector).filter(Boolean))];
        return uniqueSectors.sort();
    }, [companies]);

    // Compute pe_ratio on the fly for each company
    const enrichedCompanies = useMemo(() => {
        return companies.map(company => {
            const trailingPe = parseFloat(company.trailing_pe);
            const forwardPe = parseFloat(company.forward_pe);
            let peRatio = null;
            let peRatioFmt = 'N/A';

            if (!isNaN(trailingPe) && !isNaN(forwardPe) && forwardPe > 0) {
                peRatio = trailingPe / forwardPe;
                peRatioFmt = peRatio.toFixed(2) + 'x';
            }

            return {
                ...company,
                pe_ratio: peRatio,
                pe_ratio_fmt: peRatioFmt
            };
        });
    }, [companies]);

    // Apply filters
    const filteredCompanies = useMemo(() => {
        return enrichedCompanies.filter(company => {
            // Sector filter
            if (filters.sector && company.sector !== filters.sector) return false;

            // Forward P/E filter
            if (filters.forwardPeMin || filters.forwardPeMax) {
                const pe = parseFloat(company.forward_pe);
                if (isNaN(pe)) return false;
                if (filters.forwardPeMin && pe < parseFloat(filters.forwardPeMin)) return false;
                if (filters.forwardPeMax && pe > parseFloat(filters.forwardPeMax)) return false;
            }

            // Trailing P/E filter
            if (filters.trailingPeMin || filters.trailingPeMax) {
                const pe = parseFloat(company.trailing_pe);
                if (isNaN(pe)) return false;
                if (filters.trailingPeMin && pe < parseFloat(filters.trailingPeMin)) return false;
                if (filters.trailingPeMax && pe > parseFloat(filters.trailingPeMax)) return false;
            }

            // Market Cap filter (in billions)
            if (filters.marketCapMin || filters.marketCapMax) {
                const cap = parseFloat(company.market_cap);
                if (isNaN(cap)) return false;
                const capBillions = cap / 1e9;
                if (filters.marketCapMin && capBillions < parseFloat(filters.marketCapMin)) return false;
                if (filters.marketCapMax && capBillions > parseFloat(filters.marketCapMax)) return false;
            }

            // Profit Margin filter (as percentage)
            if (filters.profitMarginMin || filters.profitMarginMax) {
                const margin = parseFloat(company.profit_margin);
                if (isNaN(margin)) return false;
                const marginPct = margin * 100;
                if (filters.profitMarginMin && marginPct < parseFloat(filters.profitMarginMin)) return false;
                if (filters.profitMarginMax && marginPct > parseFloat(filters.profitMarginMax)) return false;
            }

            // Revenue Growth filter (as percentage)
            if (filters.revenueGrowthMin || filters.revenueGrowthMax) {
                const growth = parseFloat(company.revenue_growth);
                if (isNaN(growth)) return false;
                const growthPct = growth * 100;
                if (filters.revenueGrowthMin && growthPct < parseFloat(filters.revenueGrowthMin)) return false;
                if (filters.revenueGrowthMax && growthPct > parseFloat(filters.revenueGrowthMax)) return false;
            }

            // P/E Ratio filter (trailing/forward)
            if (filters.peRatioMin || filters.peRatioMax) {
                const ratio = parseFloat(company.pe_ratio);
                if (isNaN(ratio)) return false;
                if (filters.peRatioMin && ratio < parseFloat(filters.peRatioMin)) return false;
                if (filters.peRatioMax && ratio > parseFloat(filters.peRatioMax)) return false;
            }

            // Year Change filter (as percentage)
            if (filters.yearChangeMin || filters.yearChangeMax) {
                const change = parseFloat(company.year_change);
                if (isNaN(change)) return false;
                const changePct = change * 100;
                if (filters.yearChangeMin && changePct < parseFloat(filters.yearChangeMin)) return false;
                if (filters.yearChangeMax && changePct > parseFloat(filters.yearChangeMax)) return false;
            }

            // EPS filter
            if (filters.epsMin || filters.epsMax) {
                const eps = parseFloat(company.eps);
                if (isNaN(eps)) return false;
                if (filters.epsMin && eps < parseFloat(filters.epsMin)) return false;
                if (filters.epsMax && eps > parseFloat(filters.epsMax)) return false;
            }

            // Beta filter
            if (filters.betaMin || filters.betaMax) {
                const beta = parseFloat(company.beta);
                if (isNaN(beta)) return false;
                if (filters.betaMin && beta < parseFloat(filters.betaMin)) return false;
                if (filters.betaMax && beta > parseFloat(filters.betaMax)) return false;
            }

            // 52 Week High filter
            if (filters.fiftyTwoWeekHighMin || filters.fiftyTwoWeekHighMax) {
                const high = parseFloat(company.fifty_two_week_high);
                if (isNaN(high)) return false;
                if (filters.fiftyTwoWeekHighMin && high < parseFloat(filters.fiftyTwoWeekHighMin)) return false;
                if (filters.fiftyTwoWeekHighMax && high > parseFloat(filters.fiftyTwoWeekHighMax)) return false;
            }

            // 52 Week Low filter
            if (filters.fiftyTwoWeekLowMin || filters.fiftyTwoWeekLowMax) {
                const low = parseFloat(company.fifty_two_week_low);
                if (isNaN(low)) return false;
                if (filters.fiftyTwoWeekLowMin && low < parseFloat(filters.fiftyTwoWeekLowMin)) return false;
                if (filters.fiftyTwoWeekLowMax && low > parseFloat(filters.fiftyTwoWeekLowMax)) return false;
            }

            // Dividend Yield filter (as percentage)
            if (filters.dividendYieldMin || filters.dividendYieldMax) {
                const yieldVal = parseFloat(company.dividend_yield);
                if (isNaN(yieldVal)) return false;
                const yieldPct = yieldVal * 100;
                if (filters.dividendYieldMin && yieldPct < parseFloat(filters.dividendYieldMin)) return false;
                if (filters.dividendYieldMax && yieldPct > parseFloat(filters.dividendYieldMax)) return false;
            }

            // Day Change filter (as percentage)
            if (filters.dayChangePercentMin || filters.dayChangePercentMax) {
                const dayChange = parseFloat(company.day_change_percent);
                if (isNaN(dayChange)) return false;
                if (filters.dayChangePercentMin && dayChange < parseFloat(filters.dayChangePercentMin)) return false;
                if (filters.dayChangePercentMax && dayChange > parseFloat(filters.dayChangePercentMax)) return false;
            }

            return true;
        });
    }, [enrichedCompanies, filters]);

    const sortedCompanies = useMemo(() => {
        return [...filteredCompanies].sort((a, b) => {
            let aVal = a[sortField];
            let bVal = b[sortField];

            // Handle null/undefined values
            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;

            // Convert to numbers if possible
            if (typeof aVal === 'string' && !isNaN(parseFloat(aVal))) {
                aVal = parseFloat(aVal);
                bVal = parseFloat(bVal);
            }

            if (sortOrder === 'asc') {
                return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            }
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        });
    }, [filteredCompanies, sortField, sortOrder]);

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon active">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
    };

    if (loading) {
        return (
            <div className="table-loading">
                <div className="spinner"></div>
                <p>Loading companies...</p>
            </div>
        );
    }

    return (
        <div className="company-table-wrapper fade-in">
            <div className="table-header">
                <h3>{sortedCompanies.length} Companies{hasActiveFilters && ` (filtered from ${companies.length})`}</h3>
                {(showAll || companies.length > 10) && (
                    <button
                        className={`btn btn-filter ${showFilters ? 'active' : ''}`}
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        {showFilters ? 'Hide Filters' : 'Show Filters'}
                    </button>
                )}
            </div>

            {showFilters && (
                <div className="filter-panel">
                    <div className="filter-row">
                        <div className="filter-group">
                            <label>Sector</label>
                            <select name="sector" value={filters.sector} onChange={handleFilterChange}>
                                <option value="">All Sectors</option>
                                {sectors.map(s => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </select>
                        </div>

                        <div className="filter-group">
                            <label>Forward P/E</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="forwardPeMin"
                                    placeholder="Min"
                                    value={filters.forwardPeMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="forwardPeMax"
                                    placeholder="Max"
                                    value={filters.forwardPeMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Trailing P/E</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="trailingPeMin"
                                    placeholder="Min"
                                    value={filters.trailingPeMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="trailingPeMax"
                                    placeholder="Max"
                                    value={filters.trailingPeMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row">
                        <div className="filter-group">
                            <label>Market Cap (Billions $)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="marketCapMin"
                                    placeholder="Min"
                                    value={filters.marketCapMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="marketCapMax"
                                    placeholder="Max"
                                    value={filters.marketCapMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Profit Margin (%)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="profitMarginMin"
                                    placeholder="Min"
                                    value={filters.profitMarginMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="profitMarginMax"
                                    placeholder="Max"
                                    value={filters.profitMarginMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Revenue Growth (%)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="revenueGrowthMin"
                                    placeholder="Min"
                                    value={filters.revenueGrowthMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="revenueGrowthMax"
                                    placeholder="Max"
                                    value={filters.revenueGrowthMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row">
                        <div className="filter-group">
                            <label>P/E Ratio (Trail/Fwd)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    step="0.1"
                                    name="peRatioMin"
                                    placeholder="Min"
                                    value={filters.peRatioMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    step="0.1"
                                    name="peRatioMax"
                                    placeholder="Max"
                                    value={filters.peRatioMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>52W Change (%)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="yearChangeMin"
                                    placeholder="Min"
                                    value={filters.yearChangeMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="yearChangeMax"
                                    placeholder="Max"
                                    value={filters.yearChangeMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row">
                        <div className="filter-group">
                            <label>Beta</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    step="0.1"
                                    name="betaMin"
                                    placeholder="Min"
                                    value={filters.betaMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    step="0.1"
                                    name="betaMax"
                                    placeholder="Max"
                                    value={filters.betaMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>EPS ($)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    step="0.01"
                                    name="epsMin"
                                    placeholder="Min"
                                    value={filters.epsMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    step="0.01"
                                    name="epsMax"
                                    placeholder="Max"
                                    value={filters.epsMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Div Yield (%)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    step="0.1"
                                    name="dividendYieldMin"
                                    placeholder="Min"
                                    value={filters.dividendYieldMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    step="0.1"
                                    name="dividendYieldMax"
                                    placeholder="Max"
                                    value={filters.dividendYieldMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-row">
                        <div className="filter-group">
                            <label>52W High ($)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="fiftyTwoWeekHighMin"
                                    placeholder="Min"
                                    value={filters.fiftyTwoWeekHighMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="fiftyTwoWeekHighMax"
                                    placeholder="Max"
                                    value={filters.fiftyTwoWeekHighMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>52W Low ($)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    name="fiftyTwoWeekLowMin"
                                    placeholder="Min"
                                    value={filters.fiftyTwoWeekLowMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    name="fiftyTwoWeekLowMax"
                                    placeholder="Max"
                                    value={filters.fiftyTwoWeekLowMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Day Change (%)</label>
                            <div className="range-inputs">
                                <input
                                    type="number"
                                    step="0.1"
                                    name="dayChangePercentMin"
                                    placeholder="Min"
                                    value={filters.dayChangePercentMin}
                                    onChange={handleFilterChange}
                                />
                                <span>to</span>
                                <input
                                    type="number"
                                    step="0.1"
                                    name="dayChangePercentMax"
                                    placeholder="Max"
                                    value={filters.dayChangePercentMax}
                                    onChange={handleFilterChange}
                                />
                            </div>
                        </div>
                    </div>

                    {hasActiveFilters && (
                        <div className="filter-actions">
                            <button className="btn btn-clear" onClick={clearFilters}>
                                Clear All Filters
                            </button>
                        </div>
                    )}
                </div>
            )}

            <div className="table-container">
                <table className="company-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort('ticker')}>
                                Ticker <SortIcon field="ticker" />
                            </th>
                            <th onClick={() => handleSort('company_name')}>
                                Company <SortIcon field="company_name" />
                            </th>
                            <th onClick={() => handleSort('sector')}>
                                Sector <SortIcon field="sector" />
                            </th>
                            <th onClick={() => handleSort('current_price')} className="text-right">
                                Price <SortIcon field="current_price" />
                            </th>
                            <th onClick={() => handleSort('market_cap')} className="text-right">
                                Market Cap <SortIcon field="market_cap" />
                            </th>
                            <th onClick={() => handleSort('forward_pe')} className="text-right">
                                Fwd P/E <SortIcon field="forward_pe" />
                            </th>
                            <th onClick={() => handleSort('trailing_pe')} className="text-right">
                                Trail P/E <SortIcon field="trailing_pe" />
                            </th>
                            <th onClick={() => handleSort('pe_ratio')} className="text-right">
                                P/E Ratio <SortIcon field="pe_ratio" />
                            </th>
                            <th onClick={() => handleSort('profit_margin')} className="text-right">
                                Profit Margin <SortIcon field="profit_margin" />
                            </th>
                            <th onClick={() => handleSort('revenue_growth')} className="text-right">
                                Rev Growth <SortIcon field="revenue_growth" />
                            </th>
                            <th onClick={() => handleSort('day_change_percent')} className="text-right">
                                Day Chg <SortIcon field="day_change_percent" />
                            </th>
                            <th onClick={() => handleSort('year_change')} className="text-right">
                                52W Change <SortIcon field="year_change" />
                            </th>
                            <th onClick={() => handleSort('pct_from_high')} className="text-right">
                                From High <SortIcon field="pct_from_high" />
                            </th>
                            <th onClick={() => handleSort('fifty_two_week_high')} className="text-right">
                                52W High <SortIcon field="fifty_two_week_high" />
                            </th>
                            <th onClick={() => handleSort('fifty_two_week_low')} className="text-right">
                                52W Low <SortIcon field="fifty_two_week_low" />
                            </th>
                            <th onClick={() => handleSort('beta')} className="text-right">
                                Beta <SortIcon field="beta" />
                            </th>
                            <th onClick={() => handleSort('eps')} className="text-right">
                                EPS <SortIcon field="eps" />
                            </th>
                            <th onClick={() => handleSort('dividend_yield')} className="text-right">
                                Div Yield <SortIcon field="dividend_yield" />
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedCompanies.map((company) => (
                            <tr key={company.ticker}>
                                <td>
                                    <a
                                        href={`https://finance.yahoo.com/quote/${company.ticker}/key-statistics/`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="ticker-link"
                                    >
                                        <span className="ticker-badge font-mono">
                                            {company.ticker}
                                        </span>
                                    </a>
                                </td>
                                <td className="company-name">
                                    <span
                                        className="clickable-cell"
                                        onClick={() => onCompanySelect?.(company.ticker)}
                                    >
                                        {company.company_name}
                                    </span>
                                    <ResearchLink
                                        ticker={company.ticker}
                                        onRunResearch={onRunResearch}
                                        className="company-name-research"
                                    />
                                </td>
                                <td>
                                    <span
                                        className="sector-badge"
                                        style={{
                                            background: `${getSectorColor(company.sector)}20`,
                                            color: getSectorColor(company.sector)
                                        }}
                                    >
                                        {company.sector}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    {company.current_price_fmt || 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {company.market_cap_fmt || 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {formatNumber(company.forward_pe)}
                                </td>
                                <td className="text-right font-mono">
                                    {formatNumber(company.trailing_pe)}
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.pe_ratio > 1 ? 'value-positive' : company.pe_ratio < 1 ? 'value-negative' : ''}>
                                        {company.pe_ratio_fmt || formatNumber(company.pe_ratio)}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.profit_margin > 0 ? 'value-positive' : 'value-negative'}>
                                        {company.profit_margin_fmt || 'N/A'}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.revenue_growth > 0 ? 'value-positive' : 'value-negative'}>
                                        {company.revenue_growth_fmt || 'N/A'}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.day_change_percent > 0 ? 'value-positive' : company.day_change_percent < 0 ? 'value-negative' : ''}>
                                        {company.day_change_percent != null ? (company.day_change_percent > 0 ? '+' : '') + company.day_change_percent.toFixed(2) + '%' : 'N/A'}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.year_change > 0 ? 'value-positive' : company.year_change < 0 ? 'value-negative' : ''}>
                                        {company.year_change_fmt || (company.year_change ? (company.year_change * 100).toFixed(2) + '%' : 'N/A')}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    <span className={company.pct_from_high > -0.1 ? 'value-near-high' : company.pct_from_high < -0.2 ? 'value-negative' : 'value-neutral'}>
                                        {company.pct_from_high != null ? (company.pct_from_high * 100).toFixed(1) + '%' : 'N/A'}
                                    </span>
                                </td>
                                <td className="text-right font-mono">
                                    {company.fifty_two_week_high != null ? '$' + company.fifty_two_week_high.toFixed(2) : 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {company.fifty_two_week_low != null ? '$' + company.fifty_two_week_low.toFixed(2) : 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {company.beta != null ? company.beta.toFixed(2) : 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {company.eps != null ? '$' + company.eps.toFixed(2) : 'N/A'}
                                </td>
                                <td className="text-right font-mono">
                                    {company.dividend_yield_fmt || 'N/A'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default CompanyTable;

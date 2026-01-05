import { useState, useEffect, useMemo } from 'react';
import { fetchCompaniesBySector, fetchCompanies, getSectorColor, formatNumber, SECTOR_COLORS } from '../utils/api';
import './CompanyTable.css';

function CompanyTable({ sector, searchResults, showAll }) {
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
                        🔍 {showFilters ? 'Hide Filters' : 'Show Filters'}
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
                    </div>

                    {hasActiveFilters && (
                        <div className="filter-actions">
                            <button className="btn btn-clear" onClick={clearFilters}>
                                ✕ Clear All Filters
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
                        </tr>
                    </thead>
                    <tbody>
                        {sortedCompanies.map((company) => (
                            <tr key={company.ticker}>
                                <td>
                                    <span className="ticker-badge font-mono">
                                        {company.ticker}
                                    </span>
                                </td>
                                <td className="company-name">{company.company_name}</td>
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
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default CompanyTable;

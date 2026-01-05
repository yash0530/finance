import { useState, useEffect } from 'react';
import { fetchCompaniesBySector, getSectorColor, formatNumber } from '../utils/api';
import './CompanyTable.css';

function CompanyTable({ sector, searchResults }) {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortField, setSortField] = useState('forward_pe');
    const [sortOrder, setSortOrder] = useState('asc');

    useEffect(() => {
        async function loadCompanies() {
            if (searchResults) {
                setCompanies(searchResults);
                setLoading(false);
                return;
            }

            if (!sector) return;

            try {
                setLoading(true);
                const data = await fetchCompaniesBySector(sector);
                setCompanies(data.data);
            } catch (err) {
                console.error('Failed to load companies:', err);
            } finally {
                setLoading(false);
            }
        }

        loadCompanies();
    }, [sector, searchResults]);

    const handleSort = (field) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
    };

    const sortedCompanies = [...companies].sort((a, b) => {
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
                <h3>{companies.length} Companies</h3>
            </div>

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

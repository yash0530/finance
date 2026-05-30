import { useState, useEffect, useCallback } from 'react';
import Dashboard from '../components/Dashboard';
import CompanyTable from '../components/CompanyTable';
import SectorChart from '../components/SectorChart';
import SearchBar from '../components/SearchBar';
import MetricsPanel from '../components/MetricsPanel';
import SpotlightPanel from '../components/SpotlightPanel';
import { fetchSectors, fetchStats, fetchSpotlightCategory, refreshData } from '../utils/api';

function formatSnapshot(timestamp) {
    if (!timestamp) return 'Snapshot not refreshed yet';
    const d = new Date(timestamp);
    if (Number.isNaN(d.getTime())) return `Snapshot ${timestamp}`;
    return `Snapshot ${d.toLocaleString()}`;
}

export default function MarketPage({ onSelectTicker, onOpenScreenerPreset }) {
    const [sectors, setSectors] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchResults, setSearchResults] = useState(null);
    const [selectedSector, setSelectedSector] = useState(null);
    const [showAllCompanies, setShowAll] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [refreshMsg, setRefreshMsg] = useState(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const [sectorsData, statsData] = await Promise.all([fetchSectors(), fetchStats()]);
            setSectors(sectorsData.data || []);
            setStats(statsData);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const openTicker = useCallback((ticker) => {
        onSelectTicker?.(ticker);
    }, [onSelectTicker]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        setRefreshMsg(null);
        try {
            const result = await refreshData();
            const rows = result?.result?.data?.row_count;
            setRefreshMsg({ type: 'success', text: rows ? `S&P 500 snapshot refreshed: ${rows} rows.` : 'S&P 500 snapshot refreshed.' });
            await load();
        } catch (err) {
            setRefreshMsg({ type: 'error', text: err.message });
        } finally {
            setRefreshing(false);
            setTimeout(() => setRefreshMsg(null), 5000);
        }
    }, [load]);

    const openSpotlight = useCallback(async (category) => {
        try {
            const result = await fetchSpotlightCategory(category);
            setSearchResults({ count: result.count, data: result.companies || [], label: result.title });
            setSelectedSector(null);
            setShowAll(false);
        } catch (err) {
            setRefreshMsg({ type: 'error', text: err.message });
        }
    }, []);

    const back = useCallback(() => {
        setSelectedSector(null);
        setSearchResults(null);
        setShowAll(false);
    }, []);

    if (loading) {
        return <div className="loading-state"><div className="spinner" /><span>Loading S&amp;P 500 data...</span></div>;
    }

    if (error) {
        return <div className="alert alert-error">{error}</div>;
    }

    const tableTitle = searchResults
        ? `${searchResults.label || 'Results'} (${searchResults.count})`
        : showAllCompanies
            ? 'All Companies'
            : selectedSector;

    return (
        <div className="fade-in">
            <div className="page-header" style={{ flexWrap: 'wrap' }}>
                <div>
                    <h1 className="page-title">S&amp;P 500 Intelligence</h1>
                    <p className="page-subtitle">
                        {stats?.total_companies || 0} companies tracked · {formatSnapshot(stats?.snapshot?.timestamp)}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end', flex: '1 1 320px' }}>
                    <SearchBar onResults={r => { setSearchResults({ ...r, label: 'Search results' }); setSelectedSector(null); setShowAll(false); }} />
                    <button id="btn-refresh-market" className="btn btn-secondary" onClick={handleRefresh} disabled={refreshing}>
                        {refreshing ? <><span className="spinner spinner-sm" /> Refreshing...</> : 'Refresh'}
                    </button>
                </div>
            </div>

            {refreshMsg && (
                <div className={`alert alert-${refreshMsg.type}`} style={{ marginBottom: 'var(--spacing-md)' }}>
                    {refreshMsg.text}
                </div>
            )}

            {!selectedSector && !searchResults && !showAllCompanies ? (
                <>
                    <div style={{ display: 'flex', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-lg)', flexWrap: 'wrap' }}>
                        <button id="btn-all-companies" className="btn btn-primary" onClick={() => setShowAll(true)}>
                            All Companies
                        </button>
                        <button
                            id="btn-patterns"
                            className="btn btn-secondary"
                            onClick={() => onOpenScreenerPreset?.('Pattern: Head & Shoulders (S&P)')}
                        >
                            Technical Patterns
                        </button>
                    </div>
                    <SpotlightPanel onCompanySelect={openTicker} onCategorySelect={openSpotlight} />
                    <MetricsPanel stats={stats} onCompanySelect={openTicker} />
                    <Dashboard sectors={sectors} onSectorSelect={s => { setSelectedSector(s); setSearchResults(null); }} />
                    <SectorChart sectors={sectors} />
                </>
            ) : (
                <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
                        <button className="btn btn-secondary" onClick={back}>Back</button>
                        <h2 style={{ fontSize: '1.1rem' }}>{tableTitle}</h2>
                    </div>
                    <CompanyTable
                        sector={selectedSector}
                        searchResults={searchResults?.data}
                        showAll={showAllCompanies}
                        onCompanySelect={openTicker}
                    />
                </>
            )}
        </div>
    );
}

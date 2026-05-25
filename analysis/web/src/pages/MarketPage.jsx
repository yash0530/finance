/**
 * MarketPage.jsx — Wraps all the existing S&P 500 analysis components
 * under the new sidebar layout without breaking any existing functionality.
 */
import { useState, useEffect } from 'react';
import Dashboard from '../components/Dashboard';
import CompanyTable from '../components/CompanyTable';
import SectorChart from '../components/SectorChart';
import SearchBar from '../components/SearchBar';
import MetricsPanel from '../components/MetricsPanel';
import SpotlightPanel from '../components/SpotlightPanel';
import SpotlightDashboard from '../components/SpotlightDashboard';
import TechnicalPatternsDashboard from '../components/TechnicalPatternsDashboard';
import CompanyDetail from '../components/CompanyDetail';
import { fetchSectors, fetchStats, healthCheck, refreshData } from '../utils/api';

export default function MarketPage() {
    const [sectors, setSectors]   = useState([]);
    const [stats, setStats]       = useState(null);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState(null);
    const [searchResults, setSearchResults] = useState(null);
    const [selectedSector, setSelectedSector] = useState(null);
    const [showAllCompanies, setShowAll]       = useState(false);
    const [refreshing, setRefreshing]         = useState(false);
    const [refreshMsg, setRefreshMsg]         = useState(null);
    const [selectedCompany, setSelectedCompany] = useState(null);
    const [selectedSpotlight, setSelectedSpotlight] = useState(null);
    const [showPatterns, setShowPatterns]           = useState(false);

    useEffect(() => {
        async function load() {
            try {
                setLoading(true); setError(null);
                const [sectorsData, statsData] = await Promise.all([fetchSectors(), fetchStats()]);
                setSectors(sectorsData.data);
                setStats(statsData);
            } catch (err) { setError(err.message); }
            finally { setLoading(false); }
        }
        load();
    }, []);

    async function handleRefresh() {
        setRefreshing(true); setRefreshMsg(null);
        try {
            const result = await refreshData();
            setRefreshMsg({ type: 'success', text: result.message });
            const [s, st] = await Promise.all([fetchSectors(), fetchStats()]);
            setSectors(s.data); setStats(st);
        } catch (err) { setRefreshMsg({ type: 'error', text: err.message }); }
        finally {
            setRefreshing(false);
            setTimeout(() => setRefreshMsg(null), 5000);
        }
    }

    function back() {
        setSelectedSector(null); setSearchResults(null);
        setShowAll(false); setSelectedCompany(null);
        setSelectedSpotlight(null); setShowPatterns(false);
    }

    if (loading) return <div className="loading-state"><div className="spinner" /><span>Loading S&P 500 data…</span></div>;
    if (error)   return <div className="alert alert-error">{error}</div>;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">S&amp;P 500 Analysis</h1>
                    <p className="page-subtitle">{stats?.total_companies} companies tracked</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
                    <SearchBar onResults={r => { setSearchResults(r); setSelectedSector(null); }} />
                    <button id="btn-refresh-market" className="btn btn-secondary" onClick={handleRefresh} disabled={refreshing}>
                        {refreshing ? <><span className="spinner spinner-sm" /> Refreshing…</> : 'Refresh'}
                    </button>
                </div>
            </div>

            {refreshMsg && (
                <div className={`alert alert-${refreshMsg.type}`} style={{ marginBottom: 'var(--spacing-md)' }}>
                    {refreshMsg.text}
                </div>
            )}

            {selectedCompany ? (
                <CompanyDetail ticker={selectedCompany} onBack={back} />
            ) : selectedSpotlight ? (
                <SpotlightDashboard category={selectedSpotlight} onBack={back} onCompanySelect={setSelectedCompany} />
            ) : showPatterns ? (
                <TechnicalPatternsDashboard onBack={back} onCompanySelect={setSelectedCompany} />
            ) : !selectedSector && !searchResults && !showAllCompanies ? (
                <>
                    <div style={{ display: 'flex', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-lg)' }}>
                        <button id="btn-all-companies" className="btn btn-primary" onClick={() => setShowAll(true)}>
                            All Companies
                        </button>
                        <button id="btn-patterns" className="btn btn-secondary" onClick={() => setShowPatterns(true)}>
                            Technical Patterns
                        </button>
                    </div>
                    <SpotlightPanel onCompanySelect={setSelectedCompany} onCategorySelect={setSelectedSpotlight} />
                    <MetricsPanel stats={stats} onCompanySelect={setSelectedCompany} />
                    <Dashboard sectors={sectors} onSectorSelect={s => { setSelectedSector(s); setSearchResults(null); }} />
                    <SectorChart sectors={sectors} />
                </>
            ) : (
                <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
                        <button className="btn btn-secondary" onClick={back}>← Back</button>
                        <h2 style={{ fontSize: '1.1rem' }}>
                            {searchResults ? `Results (${searchResults.count})` : showAllCompanies ? 'All Companies' : selectedSector}
                        </h2>
                    </div>
                    <CompanyTable
                        sector={selectedSector}
                        searchResults={searchResults?.data}
                        showAll={showAllCompanies}
                        onCompanySelect={setSelectedCompany}
                    />
                </>
            )}
        </div>
    );
}

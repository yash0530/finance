import { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import CompanyTable from './components/CompanyTable';
import SectorChart from './components/SectorChart';
import SearchBar from './components/SearchBar';
import MetricsPanel from './components/MetricsPanel';
import { fetchSectors, fetchStats, healthCheck } from './utils/api';

function App() {
  const [sectors, setSectors] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Check API health first
        await healthCheck();

        // Fetch all data
        const [sectorsData, statsData] = await Promise.all([
          fetchSectors(),
          fetchStats()
        ]);

        setSectors(sectorsData.data);
        setStats(statsData);
      } catch (err) {
        setError(err.message || 'Failed to connect to API. Make sure Flask server is running on port 5000.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handleSectorSelect = (sector) => {
    setSelectedSector(sector);
    setSearchResults(null);
  };

  const handleSearchResults = (results) => {
    setSearchResults(results);
    setSelectedSector(null);
  };

  const handleBackToDashboard = () => {
    setSelectedSector(null);
    setSearchResults(null);
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Loading S&P 500 data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-error">
        <div className="error-icon">⚠️</div>
        <h2>Connection Error</h2>
        <p>{error}</p>
        <div className="error-hint">
          <p>Start the Flask server:</p>
          <code>python3 app.py</code>
        </div>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <h1>📊 S&P 500 Analysis</h1>
            <span className="tagline">Interactive Financial Playground</span>
          </div>
          <SearchBar onResults={handleSearchResults} />
        </div>
      </header>

      <main className="app-main">
        {!selectedSector && !searchResults ? (
          <>
            <MetricsPanel stats={stats} />
            <Dashboard
              sectors={sectors}
              onSectorSelect={handleSectorSelect}
            />
            <SectorChart sectors={sectors} />
          </>
        ) : (
          <>
            <div className="breadcrumb">
              <button className="btn btn-secondary" onClick={handleBackToDashboard}>
                ← Back to Dashboard
              </button>
              <h2>
                {searchResults
                  ? `Search Results (${searchResults.count})`
                  : selectedSector}
              </h2>
            </div>
            <CompanyTable
              sector={selectedSector}
              searchResults={searchResults?.data}
            />
          </>
        )}
      </main>

      <footer className="app-footer">
        <p>
          Data source: Wikipedia + Yahoo Finance (yfinance) |
          {stats && ` ${stats.total_companies} companies tracked`}
        </p>
      </footer>
    </div>
  );
}

export default App;

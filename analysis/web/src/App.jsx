import { useState, useEffect, lazy, Suspense } from 'react';
import './index.css';
import './App.css';
import Sidebar from './components/Sidebar';
import { getPortfolioStatus } from './utils/api';

// Lazy-load pages for fast initial load
const PortfolioPage      = lazy(() => import('./pages/PortfolioPage'));
const AdvisorPage        = lazy(() => import('./pages/AdvisorPage'));
const DeepResearchV2Page = lazy(() => import('./pages/DeepResearchV2Page'));
const DeepResearchPage   = lazy(() => import('./pages/DeepResearchPage'));
const ResearchPage      = lazy(() => import('./pages/ResearchPage'));
const ResearchHistoryPage = lazy(() => import('./pages/ResearchHistoryPage'));
const WatchlistPage     = lazy(() => import('./pages/WatchlistPage'));
const RebalancePage     = lazy(() => import('./pages/RebalancePage'));
const CalibrationPage   = lazy(() => import('./pages/CalibrationPage'));
const AlertsPage        = lazy(() => import('./pages/AlertsPage'));
const LLMSettingsPage   = lazy(() => import('./pages/LLMSettingsPage'));

// Legacy S&P 500 pages (existing components wrapped)
const MarketPage = lazy(() => import('./pages/MarketPage'));

function PageLoader() {
    return (
        <div className="loading-state" style={{ minHeight: '60vh' }}>
            <div className="spinner" />
            <span style={{ color: 'var(--text-muted)', fontSize: '0.825rem' }}>Loading…</span>
        </div>
    );
}

export default function App() {
    const [page, setPage] = useState('portfolio');
    const [portfolioConnected, setPortfolioConnected] = useState(false);

    // Poll portfolio connection status
    useEffect(() => {
        async function checkStatus() {
            try {
                const status = await getPortfolioStatus();
                setPortfolioConnected(status.connected && status.holdings_count > 0);
            } catch {
                setPortfolioConnected(false);
            }
        }
        checkStatus();
        const interval = setInterval(checkStatus, 60_000);
        return () => clearInterval(interval);
    }, []);

    function renderPage() {
        switch (page) {
            case 'portfolio':       return <PortfolioPage onConnected={() => setPortfolioConnected(true)} />;
            case 'advisor':        return <AdvisorPage />;
            case 'deep-research-v2':return <DeepResearchV2Page />;
            case 'deep-research':   return <DeepResearchPage />;
            case 'research':       return <ResearchPage />;
            case 'history':        return <ResearchHistoryPage />;
            case 'watchlist':      return <WatchlistPage onResearch={(t) => setPage('research')} />;
            case 'rebalance':      return <RebalancePage />;
            case 'calibration':    return <CalibrationPage />;
            case 'alerts':         return <AlertsPage />;
            case 'market':         return <MarketPage />;
            case 'settings':       return <LLMSettingsPage />;
            default:               return <PortfolioPage onConnected={() => setPortfolioConnected(true)} />;
        }
    }

    return (
        <div className="app-shell">
            <Sidebar
                currentPage={page}
                onNavigate={setPage}
                portfolioConnected={portfolioConnected}
            />
            <main className="main-content">
                <div className="page-content">
                    <Suspense fallback={<PageLoader />}>
                        {renderPage()}
                    </Suspense>
                </div>
            </main>
        </div>
    );
}

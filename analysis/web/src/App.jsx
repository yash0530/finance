import { useState, useEffect, lazy, Suspense } from 'react';
import './index.css';
import './App.css';
import Sidebar from './components/Sidebar';
import { getPortfolioStatus, getVersion } from './utils/api';

// Lazy-load pages for fast initial load
const PortfolioPage      = lazy(() => import('./pages/PortfolioPage'));
const AdvisorPage        = lazy(() => import('./pages/AdvisorPage'));
const DeepResearchPage   = lazy(() => import('./pages/DeepResearchPage'));
const QuickResearchPage  = lazy(() => import('./pages/QuickResearchPage'));
const ResearchPage      = lazy(() => import('./pages/ResearchPage'));
const ResearchHistoryPage = lazy(() => import('./pages/ResearchHistoryPage'));
const WatchlistPage     = lazy(() => import('./pages/WatchlistPage'));
const RebalancePage     = lazy(() => import('./pages/RebalancePage'));
const CalibrationPage   = lazy(() => import('./pages/CalibrationPage'));
const AlertsPage        = lazy(() => import('./pages/AlertsPage'));
const DocsPage          = lazy(() => import('./pages/DocsPage'));
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
    const [bootSha, setBootSha] = useState(null);
    const [liveSha, setLiveSha] = useState(null);

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

    // Detect a stale backend: if the live SHA diverges from the SHA at page-load
    // time, the backend has restarted (likely with new code). Show a banner so
    // the user knows their tab is out of sync — don't auto-refresh because they
    // may be mid-stream on Deep Research.
    useEffect(() => {
        let cancelled = false;
        async function poll() {
            try {
                const v = await getVersion();
                if (cancelled) return;
                setLiveSha(v.git_sha);
                setBootSha(prev => prev ?? v.git_sha);
            } catch {
                // Backend down — leave shas unchanged so we don't false-alarm.
            }
        }
        poll();
        const id = setInterval(poll, 60_000);
        return () => { cancelled = true; clearInterval(id); };
    }, []);

    const backendStale = bootSha && liveSha && bootSha !== liveSha;

    function renderPage() {
        switch (page) {
            case 'portfolio':       return <PortfolioPage onConnected={() => setPortfolioConnected(true)} />;
            case 'advisor':        return <AdvisorPage />;
            case 'deep-research':   return <DeepResearchPage />;
            case 'quick-research':  return <QuickResearchPage />;
            case 'research':       return <ResearchPage />;
            case 'history':        return <ResearchHistoryPage />;
            case 'watchlist':      return <WatchlistPage onResearch={(t) => setPage('research')} />;
            case 'rebalance':      return <RebalancePage />;
            case 'calibration':    return <CalibrationPage />;
            case 'alerts':         return <AlertsPage />;
            case 'docs':           return <DocsPage />;
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
                {backendStale && (
                    <div
                        id="stale-backend-banner"
                        style={{
                            background: 'var(--accent-yellow, #f59e0b)',
                            color: '#000',
                            padding: '8px 16px',
                            fontSize: '0.82rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: 12,
                        }}
                    >
                        <span>
                             Backend was updated (was <code>{bootSha}</code>, now <code>{liveSha}</code>).
                            Refresh to pick up new endpoints.
                        </span>
                        <button
                            className="btn btn-secondary"
                            style={{ padding: '2px 10px', fontSize: '0.78rem' }}
                            onClick={() => window.location.reload()}
                        >
                            Refresh
                        </button>
                    </div>
                )}
                <div className="page-content">
                    <Suspense fallback={<PageLoader />}>
                        {renderPage()}
                    </Suspense>
                </div>
            </main>
        </div>
    );
}

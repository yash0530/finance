import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import './index.css';
import './App.css';
import Sidebar from './components/Sidebar';
import { useHashRoute } from './hooks/useHashRoute';
import { getVersion } from './utils/api';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';



const TerminalPage   = lazy(() => import('./pages/TerminalPage'));
const MarketPage     = lazy(() => import('./pages/MarketPage'));
const StockViewPage  = lazy(() => import('./pages/StockViewPage'));
const DeepResearchPage = lazy(() => import('./pages/DeepResearchPage'));
const ConsolePage    = lazy(() => import('./pages/ConsolePage'));
const LibraryPage    = lazy(() => import('./pages/LibraryPage'));
const ScreenerPage   = lazy(() => import('./pages/ScreenerPage'));
const TechnicalPatternsPage = lazy(() => import('./pages/TechnicalPatternsPage'));
const PortfolioPage  = lazy(() => import('./pages/PortfolioPage'));
const CalibrationPage = lazy(() => import('./pages/CalibrationPage'));
const SettingsPage   = lazy(() => import('./pages/SettingsPage'));
const DocsPage       = lazy(() => import('./pages/DocsPage'));

function PageLoader() {
    return (
        <div className="loading-state" style={{ minHeight: '60vh' }}>
            <div className="spinner" />
            <span style={{ color: 'var(--text-muted)', fontSize: '0.825rem' }}>Loading…</span>
        </div>
    );
}

export default function App() {
    const { page, params, go } = useHashRoute();
    const [bootSha, setBootSha] = useState(null);
    const [liveSha, setLiveSha] = useState(null);
    const [pendingCommand, setPendingCommand] = useState(null);

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

    const selectTicker = useCallback((ticker) => {
        go('stock', { t: ticker });
    }, [go]);

    const runCommand = useCallback((cmd) => {
        setPendingCommand(cmd);
        go('console');
    }, [go]);

    const runResearch = useCallback((ticker) => {
        go('research', { t: ticker });
    }, [go]);

    const openScreenerPreset = useCallback((preset) => {
        go('screener', { preset });
    }, [go]);

    const openPatterns = useCallback(() => {
        go('patterns');
    }, [go]);

    function renderPage() {
        switch (page) {
            case 'market':    return <ErrorBoundary><MarketPage onSelectTicker={selectTicker} onOpenScreenerPreset={openScreenerPreset} onOpenPatterns={openPatterns} /></ErrorBoundary>;
            case 'terminal':  return <ErrorBoundary><TerminalPage onSelectTicker={selectTicker} /></ErrorBoundary>;
            case 'stock':     return <ErrorBoundary><StockViewPage ticker={params.t} onRunCommand={runCommand} onRunResearch={runResearch} onSelectTicker={selectTicker} /></ErrorBoundary>;
            case 'research':  return <ErrorBoundary><DeepResearchPage initialTicker={params.t} /></ErrorBoundary>;
            case 'console':   return <ErrorBoundary><ConsolePage initialCommand={pendingCommand} onCommandConsumed={() => setPendingCommand(null)} /></ErrorBoundary>;
            case 'portfolio': return <ErrorBoundary><PortfolioPage onSelectTicker={selectTicker} /></ErrorBoundary>;
            case 'library':   return <ErrorBoundary><LibraryPage /></ErrorBoundary>;
            case 'screener':  return <ErrorBoundary><ScreenerPage onSelectTicker={selectTicker} presetName={params.preset} /></ErrorBoundary>;
            case 'patterns':  return <ErrorBoundary><TechnicalPatternsPage onSelectTicker={selectTicker} /></ErrorBoundary>;
            case 'review':    return <ErrorBoundary><CalibrationPage /></ErrorBoundary>;
            case 'settings':  return <ErrorBoundary><SettingsPage /></ErrorBoundary>;
            case 'docs':      return <ErrorBoundary><DocsPage /></ErrorBoundary>;
            default:          return <ErrorBoundary><MarketPage onSelectTicker={selectTicker} onOpenScreenerPreset={openScreenerPreset} onOpenPatterns={openPatterns} /></ErrorBoundary>;
        }
    }

    return (
        <ToastProvider>
            <div className="app-shell">
                <Sidebar currentPage={page} onNavigate={go} />
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
        </ToastProvider>
    );
}

import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import './index.css';
import './App.css';
import Sidebar from './components/Sidebar';
import { useHashRoute } from './hooks/useHashRoute';
import { getVersion } from './utils/api';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';



const DiscoverPage   = lazy(() => import('./pages/DiscoverPage'));
const StockViewPage  = lazy(() => import('./pages/StockViewPage'));
const DeepResearchPage = lazy(() => import('./pages/DeepResearchPage'));
const ConsolePage    = lazy(() => import('./pages/ConsolePage'));
const LibraryPage    = lazy(() => import('./pages/LibraryPage'));
const CalibrationPage = lazy(() => import('./pages/CalibrationPage'));
const SettingsPage   = lazy(() => import('./pages/SettingsPage'));
const DocsPage       = lazy(() => import('./pages/DocsPage'));

// The four discovery surfaces are now tabs inside DiscoverPage. These page ids
// remain valid hashes (deep-links, back-compat) and open Discover on that tab.
const DISCOVER_TABS = new Set(['market', 'terminal', 'screener', 'patterns']);

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
    const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
        if (typeof window === 'undefined') return false;
        return window.localStorage.getItem('edge.sidebarCollapsed') === 'true';
    });

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

    useEffect(() => {
        window.localStorage.setItem('edge.sidebarCollapsed', String(sidebarCollapsed));
    }, [sidebarCollapsed]);

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

    // Discovery surfaces collapse into one tabbed Discover page. A bare hash for
    // any tab id (e.g. #patterns) opens Discover on that tab; #discover?tab= works too.
    const discover = (tab) => (
        <ErrorBoundary>
            <DiscoverPage
                initialTab={tab}
                presetName={params.preset}
                onSelectTicker={selectTicker}
                onRunResearch={runResearch}
            />
        </ErrorBoundary>
    );

    function renderPage() {
        if (page === 'discover') return discover(params.tab);
        if (DISCOVER_TABS.has(page)) return discover(page);
        switch (page) {
            case 'stock':     return <ErrorBoundary><StockViewPage ticker={params.t} onRunCommand={runCommand} onRunResearch={runResearch} onSelectTicker={selectTicker} /></ErrorBoundary>;
            case 'research':  return <ErrorBoundary><DeepResearchPage initialTicker={params.t} /></ErrorBoundary>;
            case 'console':   return <ErrorBoundary><ConsolePage initialCommand={pendingCommand} onCommandConsumed={() => setPendingCommand(null)} /></ErrorBoundary>;
            case 'library':   return <ErrorBoundary><LibraryPage onSelectTicker={selectTicker} onRunResearch={runResearch} /></ErrorBoundary>;
            case 'review':    return <ErrorBoundary><CalibrationPage onSelectTicker={selectTicker} onRunResearch={runResearch} /></ErrorBoundary>;
            case 'settings':  return <ErrorBoundary><SettingsPage /></ErrorBoundary>;
            case 'docs':      return <ErrorBoundary><DocsPage /></ErrorBoundary>;
            default:          return discover('terminal');
        }
    }

    // Treat the back-compat tab hashes as "discover" for nav highlighting.
    const activeNav = (page === 'discover' || DISCOVER_TABS.has(page)) ? 'discover' : page;

    return (
        <ToastProvider>
            <div className={`app-shell ${sidebarCollapsed ? 'sidebar-is-collapsed' : ''}`}>
                <Sidebar
                    currentPage={activeNav}
                    onNavigate={go}
                    onSelectTicker={selectTicker}
                    onRunResearch={runResearch}
                    collapsed={sidebarCollapsed}
                    onToggleCollapsed={() => setSidebarCollapsed(collapsed => !collapsed)}
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
        </ToastProvider>
    );
}

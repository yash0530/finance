import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import './index.css';
import './App.css';
import Sidebar from './components/Sidebar';
import { useHashRoute } from './hooks/useHashRoute';
import { getVersion } from './utils/api';

const TerminalPage   = lazy(() => import('./pages/TerminalPage'));
const StockViewPage  = lazy(() => import('./pages/StockViewPage'));
const ConsolePage    = lazy(() => import('./pages/ConsolePage'));
const LibraryPage    = lazy(() => import('./pages/ResearchHistoryPage'));
const ScreenerPage   = lazy(() => import('./pages/ScreenerPage'));
const SettingsPage   = lazy(() => import('./pages/LLMSettingsPage'));
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

    function renderPage() {
        switch (page) {
            case 'terminal':  return <TerminalPage onSelectTicker={selectTicker} />;
            case 'stock':     return <StockViewPage ticker={params.t} onRunCommand={runCommand} onSelectTicker={selectTicker} />;
            case 'console':   return <ConsolePage initialCommand={pendingCommand} onCommandConsumed={() => setPendingCommand(null)} />;
            case 'library':   return <LibraryPage />;
            case 'screener':  return <ScreenerPage />;
            case 'settings':  return <SettingsPage />;
            case 'docs':      return <DocsPage />;
            default:          return <TerminalPage onSelectTicker={selectTicker} />;
        }
    }

    return (
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
    );
}

import { useState, useEffect, useCallback, lazy, Suspense } from 'react';

const TerminalPage          = lazy(() => import('./TerminalPage'));
const MarketPage            = lazy(() => import('./MarketPage'));
const ScreenerPage          = lazy(() => import('./ScreenerPage'));
const TechnicalPatternsPage = lazy(() => import('./TechnicalPatternsPage'));

const TABS = [
    { id: 'terminal', label: 'Daily Scan' },
    { id: 'market',   label: 'Market' },
    { id: 'screener', label: 'Screener' },
    { id: 'patterns', label: 'Patterns' },
];
const TAB_IDS = new Set(TABS.map(t => t.id));

/**
 * Discover — the single discovery front door. Folds the four discovery surfaces
 * (Daily Scan, Market, Screener, Patterns) into one tabbed page so the funnel
 * has one entrance instead of four. Sub-pages stay lazy-loaded, so only the
 * active tab's chunk is fetched. Tabs are conditionally rendered (state resets
 * on switch) — each sub-page already owns its own pull-based load triggers.
 */
export default function DiscoverPage({ initialTab, presetName, onSelectTicker, onRunResearch }) {
    const [tab, setTab] = useState(TAB_IDS.has(initialTab) ? initialTab : 'terminal');
    const [preset, setPreset] = useState(presetName);

    // Deep-link / alias routes drive the active tab (e.g. #patterns → Patterns).
    useEffect(() => {
        if (TAB_IDS.has(initialTab)) setTab(initialTab);
    }, [initialTab]);

    // A screener preset handoff (from a Market spotlight) jumps to the Screener tab.
    useEffect(() => {
        if (presetName) { setPreset(presetName); setTab('screener'); }
    }, [presetName]);

    const openScreenerPreset = useCallback((p) => { setPreset(p); setTab('screener'); }, []);
    const openPatterns = useCallback(() => setTab('patterns'), []);

    const common = { onSelectTicker, onRunResearch };

    return (
        <div className="fade-in">
            <div className="tabs" role="tablist" aria-label="Discover" style={{ marginBottom: 'var(--spacing-md)' }}>
                {TABS.map(t => (
                    <button
                        key={t.id}
                        id={`discover-tab-${t.id}`}
                        role="tab"
                        aria-selected={tab === t.id}
                        className={`tab-btn ${tab === t.id ? 'active' : ''}`}
                        onClick={() => setTab(t.id)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            <Suspense fallback={<div className="loading-state" style={{ minHeight: '40vh' }}><div className="spinner" /></div>}>
                {tab === 'terminal' && <TerminalPage {...common} />}
                {tab === 'market'   && <MarketPage {...common} onOpenScreenerPreset={openScreenerPreset} onOpenPatterns={openPatterns} />}
                {tab === 'screener' && <ScreenerPage {...common} presetName={preset} />}
                {tab === 'patterns' && <TechnicalPatternsPage {...common} />}
            </Suspense>
        </div>
    );
}

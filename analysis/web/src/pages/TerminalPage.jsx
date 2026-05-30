import { useState, useEffect, useCallback, useRef } from 'react';
import MoversPanel from '../components/terminal/MoversPanel';
import NewsTape from '../components/terminal/NewsTape';
import WatchlistPanel from '../components/terminal/WatchlistPanel';
import ThemeHeatPanel from '../components/terminal/ThemeHeatPanel';
import HypothesesPanel from '../components/terminal/HypothesesPanel';
import CatalystsPanel from '../components/terminal/CatalystsPanel';
import FlowPanel from '../components/terminal/FlowPanel';
import { getDashboardLayout, saveDashboardLayout } from '../utils/api';

const DEFAULT_ORDER = ['movers', 'theme-heat', 'watchlist', 'hypotheses', 'catalysts', 'news-tape', 'flow'];

const COLSPAN = { movers: 2, 'news-tape': 2 };

/**
 * Daily Scan dashboard. Pull-based: each panel refreshes manually.
 * Panels are drag-to-reorder; the order persists to dashboard_layout. The only
 * LLM spend is the Hypotheses panel's per-ticker Generate button.
 */
export default function TerminalPage({ onSelectTicker }) {
    const [order, setOrder] = useState(DEFAULT_ORDER);
    const dragItem = useRef(null);

    useEffect(() => {
        getDashboardLayout().then(res => {
            if (Array.isArray(res.layout) && res.layout.length) {
                // Keep only known panels, append any missing (forward-compatible).
                const known = new Set(DEFAULT_ORDER);
                const saved = res.layout.filter(p => known.has(p));
                const missing = DEFAULT_ORDER.filter(p => !saved.includes(p));
                setOrder([...saved, ...missing]);
            }
        }).catch(() => {});
    }, []);

    const persist = useCallback((next) => {
        setOrder(next);
        saveDashboardLayout(next).catch(() => {});
    }, []);

    const onDrop = useCallback((target) => {
        const from = dragItem.current;
        if (!from || from === target) return;
        const next = [...order];
        next.splice(next.indexOf(from), 1);
        next.splice(next.indexOf(target), 0, from);
        persist(next);
        dragItem.current = null;
    }, [order, persist]);

    const renderPanel = (id) => {
        const common = { onSelectTicker, area: id };
        switch (id) {
            case 'movers': return <MoversPanel {...common} />;
            case 'theme-heat': return <ThemeHeatPanel {...common} />;
            case 'watchlist': return <WatchlistPanel {...common} />;
            case 'hypotheses': return <HypothesesPanel {...common} />;
            case 'catalysts': return <CatalystsPanel {...common} />;
            case 'news-tape': return <NewsTape {...common} />;
            case 'flow': return <FlowPanel area={id} />;
            default: return null;
        }
    };

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Daily Scan</h1>
                    <p className="page-subtitle">Movers, themes, catalysts, news, and watchlist signals</p>
                </div>
            </div>

            <div className="terminal-grid">
                {order.map(id => (
                    <div
                        key={id}
                        draggable
                        onDragStart={() => { dragItem.current = id; }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => onDrop(id)}
                        style={{ gridColumn: `span ${COLSPAN[id] || 1}`, minHeight: 200 }}
                    >
                        {renderPanel(id)}
                    </div>
                ))}
            </div>
        </div>
    );
}

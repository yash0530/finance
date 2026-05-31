import { useState, useEffect, useCallback, useRef } from 'react';
import MoversPanel from '../components/terminal/MoversPanel';
import NewsTape from '../components/terminal/NewsTape';
import WatchlistPanel from '../components/terminal/WatchlistPanel';
import ThemeHeatPanel from '../components/terminal/ThemeHeatPanel';
import HypothesesPanel from '../components/terminal/HypothesesPanel';
import CatalystsPanel from '../components/terminal/CatalystsPanel';
import FlowPanel from '../components/terminal/FlowPanel';
import ResearchLink from '../components/ResearchLink';
import { getDashboardLayout, saveDashboardLayout, getTerminalSnapshot, formatPercent } from '../utils/api';

const DEFAULT_ORDER = ['movers', 'theme-heat', 'watchlist', 'hypotheses', 'catalysts', 'news-tape', 'flow'];

const COLSPAN = { movers: 2, 'news-tape': 2 };

/**
 * Daily Scan dashboard. Pull-based: each panel refreshes manually.
 * Panels are drag-to-reorder; the order persists to dashboard_layout. The only
 * LLM spend is the Hypotheses panel's per-ticker Generate button.
 */
export default function TerminalPage({ onSelectTicker, onRunResearch }) {
    const [order, setOrder] = useState(DEFAULT_ORDER);
    const [snapshot, setSnapshot] = useState(null);
    const [snapshotLoading, setSnapshotLoading] = useState(false);
    const [snapshotError, setSnapshotError] = useState(null);
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

    const loadSnapshot = useCallback(async () => {
        setSnapshotLoading(true);
        setSnapshotError(null);
        try {
            setSnapshot(await getTerminalSnapshot({ topN: 10, days: 7, newsLimit: 40 }));
        } catch (e) {
            setSnapshotError(e.message);
        } finally {
            setSnapshotLoading(false);
        }
    }, []);

    useEffect(() => { loadSnapshot(); }, [loadSnapshot]);

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
        const common = { onSelectTicker, onRunResearch, area: id };
        const panels = snapshot?.panels || {};
        switch (id) {
            case 'movers': return <MoversPanel {...common} initialResult={panels.movers} deferInitialLoad />;
            case 'theme-heat': return <ThemeHeatPanel {...common} initialResult={panels.theme_heat} deferInitialLoad />;
            case 'watchlist': return <WatchlistPanel {...common} />;
            case 'hypotheses': return <HypothesesPanel {...common} />;
            case 'catalysts': return <CatalystsPanel {...common} initialPayload={panels.catalysts} deferInitialLoad />;
            case 'news-tape': return <NewsTape {...common} initialResult={panels.news} deferInitialLoad />;
            case 'flow': return <FlowPanel area={id} initialStatus={panels.flow} />;
            default: return null;
        }
    };

    const brief = buildMorningBrief(snapshot);
    const queue = buildActionQueue(snapshot);

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Daily Scan</h1>
                    <p className="page-subtitle">Movers, themes, catalysts, news, and watchlist signals</p>
                </div>
                <button className="btn btn-primary" onClick={loadSnapshot} disabled={snapshotLoading}>
                    {snapshotLoading ? <span className="spinner spinner-sm" /> : 'Run Scan'}
                </button>
            </div>

            {snapshotError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{snapshotError}</div>}

            <section className="daily-scan-brief" aria-label="Morning brief">
                {brief.map(item => (
                    <div className="daily-scan-brief-tile" key={item.label}>
                        <div className="daily-scan-brief-label">{item.label}</div>
                        <div className={`daily-scan-brief-value ${item.tone || ''}`}>{item.value}</div>
                        <div className="daily-scan-brief-note">{item.note}</div>
                    </div>
                ))}
            </section>

            <section className="daily-scan-health" aria-label="Data health">
                {(snapshot?.health || defaultHealth(snapshotLoading)).map(h => (
                    <div className={`daily-scan-health-pill ${h.status || 'pending'}`} key={h.label}>
                        <span>{h.label}</span>
                        <strong>{healthLabel(h)}</strong>
                    </div>
                ))}
            </section>

            <section className="daily-scan-focus glass-card" id="panel-action-queue">
                <div className="daily-scan-focus-header">
                    <div>
                        <h3>Action Queue</h3>
                        <p>{queue.length ? `${queue.length} names with morning signals` : 'No urgent names from the current scan'}</p>
                    </div>
                    {snapshot?.as_of && <span>as of {formatTime(snapshot.as_of)}</span>}
                </div>
                {queue.length ? (
                    <div className="daily-scan-queue">
                        {queue.slice(0, 8).map(item => (
                            <div className="daily-scan-queue-row" key={item.ticker} role="button" tabIndex={0}
                                onClick={() => onSelectTicker(item.ticker)}
                                onKeyDown={(e) => { if (e.key === 'Enter') onSelectTicker(item.ticker); }}>
                                <span className="ticker-badge">{item.ticker}</span>
                                <span className="daily-scan-queue-reasons">{item.reasons.join(' / ')}</span>
                                <span className={`daily-scan-queue-score ${item.movePct >= 0 ? 'up' : 'down'}`}>
                                    {item.movePct != null ? formatPercent(item.movePct, true) : `${item.score} pts`}
                                </span>
                                <ResearchLink ticker={item.ticker} onRunResearch={onRunResearch} />
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="daily-scan-empty">Run Scan to build the queue from movers, catalysts, themes, and news.</div>
                )}
            </section>

            <div className="terminal-grid">
                {order.map(id => (
                    <div
                        key={id}
                        className={`terminal-panel-wrap ${COLSPAN[id] ? 'wide' : ''}`}
                        draggable
                        onDragStart={() => { dragItem.current = id; }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => onDrop(id)}
                        style={{ minHeight: 200 }}
                    >
                        {renderPanel(id)}
                    </div>
                ))}
            </div>
        </div>
    );
}

function buildMorningBrief(snapshot) {
    const panels = snapshot?.panels || {};
    const movers = panels.movers?.data || {};
    const themes = panels.theme_heat?.data?.themes || [];
    const news = panels.news?.data || {};
    const catalysts = panels.catalysts?.items || [];
    const quoteData = panels.quotes?.data || {};
    const topMover = [...(movers.gainers || []), ...(movers.losers || [])]
        .sort((a, b) => Math.abs(b.change_pct || 0) - Math.abs(a.change_pct || 0))[0];
    const topTheme = themes.find(t => t.median_change_pct != null);
    const nextEvent = catalysts[0];
    const flow = panels.flow || {};
    return [
        {
            label: 'Quote Coverage',
            value: quoteData.requested_count != null ? `${quoteData.resolved_count || 0}/${quoteData.requested_count}` : '-',
            note: quoteData.stale ? 'using stale-good cache' : 'resolved tickers',
            tone: quoteData.stale ? 'warn' : '',
        },
        {
            label: 'Top Move',
            value: topMover ? topMover.ticker : '-',
            note: topMover ? formatPercent(topMover.change_pct, true) : 'no mover yet',
            tone: topMover?.change_pct >= 0 ? 'up' : topMover ? 'down' : '',
        },
        {
            label: 'Theme Lead',
            value: topTheme ? topTheme.name : '-',
            note: topTheme ? formatPercent(topTheme.median_change_pct, true) : 'no theme heat',
            tone: topTheme?.median_change_pct >= 0 ? 'up' : topTheme ? 'down' : '',
        },
        {
            label: 'Next Catalyst',
            value: nextEvent ? nextEvent.event_type : '-',
            note: nextEvent ? `${nextEvent.ticker} / ${nextEvent.event_date}` : 'none in window',
        },
        {
            label: 'News',
            value: `${news.count || 0}`,
            note: 'headlines clustered by ticker',
        },
        {
            label: 'Flow',
            value: flow.status === 'available' ? 'Live' : 'On demand',
            note: flow.provider || 'free-tier',
            tone: flow.status === 'available' ? 'up' : 'warn',
        },
    ];
}

function buildActionQueue(snapshot) {
    const panels = snapshot?.panels || {};
    const movers = panels.movers?.data || {};
    const catalysts = panels.catalysts?.items || [];
    const newsItems = panels.news?.data?.items || [];
    const themes = panels.theme_heat?.data?.themes || [];
    const byTicker = new Map();

    function add(ticker, score, reason, movePct = null) {
        if (!ticker || ticker === 'MARKET') return;
        const existing = byTicker.get(ticker) || { ticker, score: 0, reasons: [], movePct };
        existing.score += score;
        if (!existing.reasons.includes(reason)) existing.reasons.push(reason);
        if (movePct != null && (existing.movePct == null || Math.abs(movePct) > Math.abs(existing.movePct))) {
            existing.movePct = movePct;
        }
        byTicker.set(ticker, existing);
    }

    [...(movers.gainers || []), ...(movers.losers || [])].forEach(row => {
        const abs = Math.abs(row.change_pct || 0);
        add(row.ticker, abs >= 5 ? 4 : abs >= 2 ? 2 : 1, `${formatPercent(row.change_pct, true)} move`, row.change_pct);
    });
    catalysts.forEach(c => add(c.ticker, c.market_wide ? 0 : 3, `${c.event_type} ${shortDate(c.event_date)}`));
    newsItems.forEach(n => add(n.ticker, 1, 'fresh news'));
    themes.forEach(t => {
        if (t.leader) add(t.leader.ticker, 1, `${t.name} leader`, t.leader.change_pct);
        if (t.laggard) add(t.laggard.ticker, 1, `${t.name} laggard`, t.laggard.change_pct);
    });

    return [...byTicker.values()].sort((a, b) => b.score - a.score || Math.abs(b.movePct || 0) - Math.abs(a.movePct || 0));
}

function defaultHealth(loading) {
    return ['Quotes', 'Movers', 'Theme heat', 'News', 'Catalysts', 'Options flow'].map(label => ({
        label,
        status: loading ? 'pending' : 'idle',
    }));
}

function healthLabel(h) {
    if (h.status === 'ok') return h.cached ? 'cached' : 'ok';
    if (h.status === 'stale') return 'stale';
    if (h.status === 'degraded') return 'degraded';
    if (h.status === 'pending') return 'loading';
    return 'idle';
}

function formatTime(iso) {
    try {
        return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return 'now';
    }
}

function shortDate(value) {
    if (!value) return '';
    return value.slice(5);
}

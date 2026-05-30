import MoversPanel from '../components/terminal/MoversPanel';
import NewsTape from '../components/terminal/NewsTape';
import WatchlistPanel from '../components/terminal/WatchlistPanel';

/**
 * Terminal — daily scan dashboard. Pull-based: each panel refreshes manually
 * via its own RefreshButton; no background polling, no LLM on mount.
 *
 * Phase 1 ships Movers, Watchlist, and News Tape. Remaining panels
 * (Theme Heat, Hypotheses, Catalysts, Flow) land in Phase 2.
 */
export default function TerminalPage({ onSelectTicker }) {
    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Terminal</h1>
                    <p className="page-subtitle">Daily scan · movers, watchlist, news · pull-based</p>
                </div>
            </div>

            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gridTemplateAreas: `
                        "movers    movers    watchlist"
                        "news-tape news-tape watchlist"
                    `,
                    gap: 'var(--spacing-md)',
                    height: 'calc(100vh - 160px)',
                }}
            >
                <MoversPanel onSelectTicker={onSelectTicker} area="movers" />
                <NewsTape onSelectTicker={onSelectTicker} area="news-tape" />
                <WatchlistPanel onSelectTicker={onSelectTicker} area="watchlist" />
            </div>
        </div>
    );
}

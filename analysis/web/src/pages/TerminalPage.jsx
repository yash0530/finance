import MoversPanel from '../components/terminal/MoversPanel';
import NewsTape from '../components/terminal/NewsTape';
import WatchlistPanel from '../components/terminal/WatchlistPanel';
import ThemeHeatPanel from '../components/terminal/ThemeHeatPanel';
import HypothesesPanel from '../components/terminal/HypothesesPanel';
import CatalystsPanel from '../components/terminal/CatalystsPanel';
import FlowPanel from '../components/terminal/FlowPanel';

/**
 * Terminal — daily scan dashboard. Pull-based: each panel refreshes manually
 * via its own RefreshButton; no background polling. The only LLM spend is the
 * Hypotheses panel's per-ticker Generate button (~$0.05, cached 4h).
 *
 * Grid layout per the v3 PRD:
 *   "movers     movers     theme-heat"
 *   "watchlist  hypotheses theme-heat"
 *   "watchlist  hypotheses catalysts"
 *   "news-tape  news-tape  flow"
 */
export default function TerminalPage({ onSelectTicker }) {
    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Terminal</h1>
                    <p className="page-subtitle">Daily scan · movers, themes, hypotheses, catalysts, flow, news · pull-based</p>
                </div>
            </div>

            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gridTemplateRows: 'minmax(220px, auto) minmax(160px, auto) minmax(160px, auto) minmax(220px, auto)',
                    gridTemplateAreas: `
                        "movers     movers     theme-heat"
                        "watchlist  hypotheses theme-heat"
                        "watchlist  hypotheses catalysts"
                        "news-tape  news-tape  flow"
                    `,
                    gap: 'var(--spacing-md)',
                }}
            >
                <MoversPanel onSelectTicker={onSelectTicker} area="movers" />
                <ThemeHeatPanel onSelectTicker={onSelectTicker} area="theme-heat" />
                <WatchlistPanel onSelectTicker={onSelectTicker} area="watchlist" />
                <HypothesesPanel onSelectTicker={onSelectTicker} area="hypotheses" />
                <CatalystsPanel onSelectTicker={onSelectTicker} area="catalysts" />
                <NewsTape onSelectTicker={onSelectTicker} area="news-tape" />
                <FlowPanel area="flow" />
            </div>
        </div>
    );
}

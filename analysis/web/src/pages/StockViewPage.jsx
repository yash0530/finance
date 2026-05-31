import StockHeader from '../components/stockview/StockHeader';
import StockChart from '../components/stockview/StockChart';
import StockCTABar from '../components/stockview/StockCTABar';
import StockQuickTake from '../components/stockview/StockQuickTake';
import StockCatalysts from '../components/stockview/StockCatalysts';
import StockTechnicals from '../components/stockview/StockTechnicals';
import FundamentalsCard from '../components/stockview/FundamentalsCard';
import OwnershipStrip from '../components/stockview/OwnershipStrip';
import FilingsNewsTimeline from '../components/stockview/FilingsNewsTimeline';
import ThemeContext from '../components/stockview/ThemeContext';
import FlowPanel from '../components/terminal/FlowPanel';
import WatchlistPanel from '../components/terminal/WatchlistPanel';
import ErrorBoundary from '../components/ErrorBoundary';

/**
 * Stock View — single-ticker cockpit. The older chart-first flow stays primary,
 * while selected-ticker signals from Daily Scan sit in the research rail.
 */
export default function StockViewPage({ ticker, onRunCommand, onRunResearch, onSelectTicker }) {
    if (!ticker) {
        return (
            <div className="fade-in">
                <div className="glass-card" style={{ cursor: 'default' }}>
                    <div className="empty-state">
                        <h3 style={{ color: 'var(--text-secondary)' }}>No ticker selected</h3>
                        <p style={{ fontSize: '0.825rem' }}>Pick a ticker from Market, Screener, or Daily Scan to open its cockpit.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in stock-workbench">
            <div className="page-header" style={{ alignItems: 'center' }}>
                <ErrorBoundary>
                    <StockHeader ticker={ticker} />
                </ErrorBoundary>
                <ErrorBoundary>
                    <StockCTABar ticker={ticker} onRunCommand={onRunCommand} onRunResearch={onRunResearch} />
                </ErrorBoundary>
            </div>

            <div className="stock-hero-grid">
                <div className="stock-main-column">
                    <ErrorBoundary>
                        <StockChart ticker={ticker} />
                    </ErrorBoundary>

                    <div className="stock-summary-grid">
                        <ErrorBoundary>
                            <FundamentalsCard ticker={ticker} />
                        </ErrorBoundary>
                        <ErrorBoundary>
                            <StockTechnicals ticker={ticker} />
                        </ErrorBoundary>
                    </div>
                </div>

                <aside className="stock-signal-rail">
                    <ErrorBoundary>
                        <StockQuickTake ticker={ticker} />
                    </ErrorBoundary>
                    <ErrorBoundary>
                        <StockCatalysts ticker={ticker} />
                    </ErrorBoundary>
                    <ErrorBoundary>
                        <FlowPanel ticker={ticker} area="stock-flow" />
                    </ErrorBoundary>
                    <ErrorBoundary>
                        <ThemeContext ticker={ticker} />
                    </ErrorBoundary>
                    <ErrorBoundary>
                        <WatchlistPanel onSelectTicker={onSelectTicker} area="stock-watchlist" />
                    </ErrorBoundary>
                </aside>
            </div>

            <div className="stock-lower-grid">
                <ErrorBoundary>
                    <OwnershipStrip ticker={ticker} />
                </ErrorBoundary>
                <ErrorBoundary>
                    <FilingsNewsTimeline ticker={ticker} />
                </ErrorBoundary>
            </div>
        </div>
    );
}

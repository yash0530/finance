import StockHeader from '../components/stockview/StockHeader';
import StockChart from '../components/stockview/StockChart';
import StockCTABar from '../components/stockview/StockCTABar';
import StockPatternBanner from '../components/stockview/StockPatternBanner';
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
 * Stock View — v2-style single-ticker detail page with our custom technical
 * chart as the primary surface and local research/pattern tools around it.
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
            <section className="stock-v2-hero glass-card">
                <div className="stock-v2-hero-main">
                    <ErrorBoundary>
                        <StockHeader ticker={ticker} />
                    </ErrorBoundary>
                </div>
                <ErrorBoundary>
                    <StockCTABar ticker={ticker} onRunCommand={onRunCommand} onRunResearch={onRunResearch} />
                </ErrorBoundary>
            </section>

            <ErrorBoundary>
                <StockPatternBanner ticker={ticker} />
            </ErrorBoundary>

            <ErrorBoundary>
                <StockChart ticker={ticker} />
            </ErrorBoundary>

            <div className="stock-summary-grid stock-v2-summary-grid">
                <ErrorBoundary>
                    <FundamentalsCard ticker={ticker} />
                </ErrorBoundary>
                <ErrorBoundary>
                    <StockTechnicals ticker={ticker} />
                </ErrorBoundary>
            </div>

            <div className="stock-research-grid">
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

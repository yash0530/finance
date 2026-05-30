import StockHeader from '../components/stockview/StockHeader';
import StockChart from '../components/stockview/StockChart';
import StockCTABar from '../components/stockview/StockCTABar';

/**
 * Stock View — single-ticker cockpit. Phase 1 ships the header, chart, and
 * CTA bar (deep-links to Console). Fundamentals, ownership, filings/news,
 * and theme context sections land in Phase 3.
 */
export default function StockViewPage({ ticker, onRunCommand }) {
    if (!ticker) {
        return (
            <div className="fade-in">
                <div className="glass-card">
                    <div className="empty-state">
                        <h3 style={{ color: 'var(--text-secondary)' }}>No ticker selected</h3>
                        <p style={{ fontSize: '0.825rem' }}>Pick a ticker from the Terminal to open its cockpit.</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="fade-in">
            <div className="page-header" style={{ alignItems: 'center' }}>
                <StockHeader ticker={ticker} />
                <StockCTABar ticker={ticker} onRunCommand={onRunCommand} />
            </div>

            <StockChart ticker={ticker} />
        </div>
    );
}

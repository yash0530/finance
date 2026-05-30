import StockHeader from '../components/stockview/StockHeader';
import StockChart from '../components/stockview/StockChart';
import StockCTABar from '../components/stockview/StockCTABar';
import FundamentalsCard from '../components/stockview/FundamentalsCard';
import OwnershipStrip from '../components/stockview/OwnershipStrip';
import FilingsNewsTimeline from '../components/stockview/FilingsNewsTimeline';
import ThemeContext from '../components/stockview/ThemeContext';

/**
 * Stock View — single-ticker cockpit. Each section lazy-fetches in parallel and
 * fails independently. No LLM spend on mount; the CTA bar deep-links to the
 * Console for on-demand reports.
 */
export default function StockViewPage({ ticker, onRunCommand }) {
    if (!ticker) {
        return (
            <div className="fade-in">
                <div className="glass-card" style={{ cursor: 'default' }}>
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

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                <StockChart ticker={ticker} />
                <FundamentalsCard ticker={ticker} />
                <OwnershipStrip ticker={ticker} />
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--spacing-lg)' }}>
                    <FilingsNewsTimeline ticker={ticker} />
                    <ThemeContext ticker={ticker} />
                </div>
            </div>
        </div>
    );
}

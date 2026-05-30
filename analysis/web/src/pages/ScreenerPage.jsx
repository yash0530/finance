/**
 * Screener — rule-based technical/fundamental screener. Full build lands in
 * Phase 5 (screener_engine + RulesBuilder + ResultsTable).
 */
export default function ScreenerPage() {
    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Screener</h1>
                    <p className="page-subtitle">Rule-based screening over cached tool data</p>
                </div>
            </div>
            <div className="glass-card" style={{ cursor: 'default' }}>
                <div className="empty-state">
                    <h3 style={{ color: 'var(--text-secondary)' }}>Coming in Phase 5</h3>
                    <p style={{ fontSize: '0.825rem', maxWidth: 460, lineHeight: 1.7 }}>
                        Build rules like "RSI &lt; 30 AND yoy_revenue_growth &gt; 0.20 in ai-infra"
                        and get a matched-tickers table.
                    </p>
                </div>
            </div>
        </div>
    );
}

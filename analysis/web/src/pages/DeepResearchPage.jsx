import React, { useState, useRef } from 'react';
import { useResearchStream, ResearchTimeline } from '../components/ResearchStream';
import FinancialTrendsChart from '../components/FinancialTrendsChart';
import ValuationCard from '../components/ValuationCard';
import RiskCard from '../components/RiskCard';

// ── Sentiment Meter (inline, same as original) ────────────
function SentimentMeter({ sentiment }) {
    if (!sentiment) return null;
    const score = sentiment.composite_score ?? 5;
    const pct = (score / 10) * 100;
    const label = sentiment.label || (score >= 6.5 ? 'bullish' : score <= 3.5 ? 'bearish' : 'neutral');
    const cls = `sentiment-${label}`;

    return (
        <div className="glass-card fade-in">
            <div className="card-header" style={{ marginBottom: 'var(--spacing-sm)' }}>
                <span className="card-title">🌡️ Market Sentiment</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.9rem' }}>
                    {score.toFixed(1)} / 10
                    <span className={`badge badge-${label === 'bullish' ? 'green' : label === 'bearish' ? 'red' : 'yellow'}`}
                        style={{ marginLeft: 8 }}>{label}</span>
                </span>
            </div>
            <div className="sentiment-bar-track">
                <div className={`sentiment-bar-fill ${cls}`} style={{ width: `${pct}%` }} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12, fontSize: '0.72rem' }}>
                {[
                    { label: 'News (40%)', val: sentiment.news_score },
                    { label: 'Analysts (35%)', val: sentiment.analyst_score, extra: sentiment.analyst_rating },
                    { label: 'Reddit (15%)', val: sentiment.reddit_score, extra: `${sentiment.reddit_mentions ?? 0} mentions` },
                ].map(s => (
                    <div key={s.label} style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: '6px 10px' }}>
                        <div style={{ color: 'var(--text-muted)' }}>{s.label}</div>
                        <div style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {s.val?.toFixed(1) ?? '—'}
                        </div>
                        {s.extra && <div style={{ color: 'var(--text-muted)' }}>{s.extra}</div>}
                    </div>
                ))}
            </div>
            {sentiment.top_headlines?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Top Headlines</div>
                    {sentiment.top_headlines.slice(0, 3).map((h, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '2px 0' }}>• {h}</div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ── Fundamentals Card ─────────────────────────────────────
function FundamentalsCard({ fund }) {
    if (!fund) return null;
    const rows = [
        ['Market Cap', fund.market_cap_fmt],
        ['Forward P/E', fund.forward_pe],
        ['Trailing P/E', fund.trailing_pe],
        ['EPS (TTM)', fund.eps != null ? `$${fund.eps}` : null],
        ['Revenue (TTM)', fund.revenue_fmt],
        ['Revenue Growth', fund.revenue_growth != null ? `${fund.revenue_growth > 0 ? '+' : ''}${fund.revenue_growth.toFixed(1)}%` : null],
        ['Profit Margin', fund.profit_margin != null ? `${fund.profit_margin.toFixed(1)}%` : null],
        ['Gross Margin', fund.gross_margin != null ? `${fund.gross_margin.toFixed(1)}%` : null],
        ['Debt/Equity', fund.debt_to_equity],
        ['Current Ratio', fund.current_ratio],
        ['Beta', fund.beta],
        ['Dividend Yield', fund.dividend_yield != null ? `${fund.dividend_yield.toFixed(2)}%` : null],
    ];

    return (
        <div className="glass-card fade-in">
            <div className="card-header">
                <span className="card-title">📊 Fundamentals</span>
            </div>
            <div className="grid grid-2" style={{ gap: 'var(--spacing-xs)' }}>
                {rows.filter(([, v]) => v != null && v !== 'N/A').map(([label, val]) => (
                    <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between',
                        padding: '6px 10px', background: 'var(--bg-secondary)',
                        borderRadius: 'var(--radius-sm)', fontSize: '0.78rem'
                    }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{String(val)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Technicals Card ───────────────────────────────────────
function TechnicalsCard({ tech }) {
    if (!tech) return null;
    const rows = [
        ['RSI (14)', tech.rsi != null ? `${tech.rsi} — ${tech.rsi_signal}` : null],
        ['MACD Signal', tech.macd?.signal_label],
        ['50-Day MA', tech.ma_50 != null ? `$${tech.ma_50}` : null],
        ['200-Day MA', tech.ma_200 != null ? `$${tech.ma_200}` : null],
        ['Golden Cross', tech.golden_cross != null ? (tech.golden_cross ? '✅ Yes' : '❌ No') : null],
        ['1Y Return', tech.year_return_pct != null ? `${tech.year_return_pct > 0 ? '+' : ''}${tech.year_return_pct.toFixed(2)}%` : null],
        ['Volatility (Ann.)', tech.annualized_volatility_pct != null ? `${tech.annualized_volatility_pct.toFixed(1)}%` : null],
    ];

    return (
        <div className="glass-card fade-in">
            <div className="card-header">
                <span className="card-title">🔧 Technical Analysis</span>
            </div>
            <div className="grid grid-2" style={{ gap: 'var(--spacing-xs)', marginBottom: tech.patterns?.length ? 'var(--spacing-md)' : 0 }}>
                {rows.filter(([, v]) => v != null).map(([label, val]) => (
                    <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between',
                        padding: '6px 10px', background: 'var(--bg-secondary)',
                        borderRadius: 'var(--radius-sm)', fontSize: '0.78rem'
                    }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{val}</span>
                    </div>
                ))}
            </div>
            {tech.patterns?.length > 0 && (
                <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
                        Detected Patterns
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {tech.patterns.map((p, i) => (
                            <span key={i} className={`badge ${p.signal?.includes('bull') ? 'badge-green' : 'badge-red'}`}>
                                {p.name} ({(p.confidence * 100).toFixed(0)}%)
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ── SEC Filing Card ───────────────────────────────────────
function EdgarCard({ edgar }) {
    if (!edgar || edgar.skipped) return null;
    if (!edgar.available && !edgar.business) {
        return (
            <div className="glass-card fade-in">
                <div className="card-header"><span className="card-title">📄 SEC Filings</span></div>
                <div className="alert alert-warning" style={{ fontSize: '0.8rem' }}>
                    {edgar.error || 'SEC filing data unavailable for this ticker'}
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            <div className="card-header" style={{ marginBottom: 0 }}>
                <span className="card-title">📄 SEC Filings</span>
                {edgar.filing_date && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {edgar.form_type} filed {edgar.filing_date}
                    </span>
                )}
            </div>
            {[
                { key: 'business', label: '🏢 Business Description' },
                { key: 'risks', label: '⚠️ Key Risk Factors' },
                { key: 'mda', label: '📈 Management Discussion & Analysis' },
            ].map(({ key, label }) => edgar[key] ? (
                <div key={key}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</div>
                    <div style={{
                        fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.8,
                        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)',
                        padding: 'var(--spacing-md)', whiteSpace: 'pre-line'
                    }}>
                        {edgar[key]}
                    </div>
                </div>
            ) : null)}
        </div>
    );
}

// ── AI Thesis Card ────────────────────────────────────────
function ThesisCard({ thesis }) {
    if (!thesis) return null;

    return (
        <div className="glass-card fade-in" style={{ borderColor: 'rgba(45, 126, 247, 0.25)' }}>
            {thesis.error && !thesis.summary ? (
                <div className="alert alert-warning">{thesis.summary || 'AI thesis unavailable'}</div>
            ) : (
                <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-md)' }}>
                        <h3 style={{ fontSize: '0.925rem', color: 'var(--text-primary)' }}>🤖 AI Investment Thesis</h3>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <span className={`badge badge-${thesis.recommendation === 'BUY' ? 'green' : thesis.recommendation === 'HOLD' ? 'yellow' : 'red'}`}
                                style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
                                {thesis.recommendation}
                            </span>
                            <span className={`badge ${
                                thesis.conviction === 'HIGH' ? 'badge-green'
                                : thesis.conviction === 'MEDIUM' ? 'badge-yellow'
                                : 'badge-gray'
                            }`} style={{ border: '1px solid', fontSize: '0.7rem' }}>
                                {thesis.conviction} conviction
                            </span>
                        </div>
                    </div>

                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: 1.7 }}>
                        {thesis.summary}
                    </p>

                    {/* Target price range */}
                    {thesis.target_price_range && (
                        <div style={{
                            display: 'flex', gap: 16, padding: '10px 14px', marginBottom: 'var(--spacing-md)',
                            background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', fontSize: '0.78rem'
                        }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>Target Range: </span>
                                <span style={{ fontFamily: 'monospace', color: 'var(--accent-green)' }}>
                                    ${thesis.target_price_range.low} — ${thesis.target_price_range.high}
                                </span>
                            </div>
                            <span style={{ color: 'var(--text-muted)' }}>({thesis.target_price_range.timeframe})</span>
                        </div>
                    )}

                    <div className="grid grid-2" style={{ gap: 'var(--spacing-md)' }}>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-green)', marginBottom: 8 }}>
                                Synthesized Bull Case
                            </div>
                            {(thesis.bull_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-green)', flexShrink: 0 }}>↑</span>{b}
                                </div>
                            ))}
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-red)', marginBottom: 8 }}>
                                Synthesized Bear Case
                            </div>
                            {(thesis.bear_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-red)', flexShrink: 0 }}>↓</span>{b}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Adversarial Debate Raw Output */}
                    {(thesis._raw_bull_pass || thesis._raw_bear_pass) && (
                        <details style={{ marginTop: 'var(--spacing-md)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 'var(--spacing-sm)' }}>
                            <summary style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', cursor: 'pointer', outline: 'none', padding: '4px 8px' }}>
                                🔍 View AI Adversarial Debate (3-Pass Output)
                            </summary>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', padding: '12px 8px 4px 8px', marginTop: 8, borderTop: '1px solid var(--border-color)' }}>
                                {thesis._raw_bull_pass && (
                                    <div>
                                        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--accent-green)', fontWeight: 700, marginBottom: 8 }}>Pass 1: The Bull</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>{thesis._raw_bull_pass}</div>
                                    </div>
                                )}
                                {thesis._raw_bear_pass && (
                                    <div>
                                        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--accent-red)', fontWeight: 700, marginBottom: 8 }}>Pass 2: The Bear</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>{thesis._raw_bear_pass}</div>
                                    </div>
                                )}
                            </div>
                        </details>
                    )}

                    {thesis.key_catalysts?.length > 0 && (
                        <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-sm) var(--spacing-md)', background: 'rgba(124,58,237,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(124,58,237,0.15)' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--accent-purple)', marginBottom: 6 }}>Key Catalysts</div>
                            {thesis.key_catalysts.map((c, i) => (
                                <div key={i} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', padding: '2px 0' }}>⚡ {c}</div>
                            ))}
                        </div>
                    )}

                    {thesis.action_items?.length > 0 && (
                        <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-md)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-blue-bright)', marginBottom: 8 }}>
                                Action Items
                            </div>
                            {thesis.action_items.map((a, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0' }}>→ {a}</div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}


// ══════════════════════════════════════════════════════════
//  MAIN PAGE COMPONENT
// ══════════════════════════════════════════════════════════
export default function DeepResearchPage() {
    const [ticker, setTicker] = useState('');
    const inputRef = useRef(null);

    const {
        stages,
        stageOrder,
        report,
        isStreaming,
        error,
        pipelineInfo,
        startResearch,
        cancel,
    } = useResearchStream();

    function handleSubmit(e) {
        e.preventDefault();
        const t = ticker.trim().toUpperCase();
        if (!t) return;
        startResearch(t);
    }

    // Extract stage data for rendering
    const fundamentals = stages.fundamentals?.data;
    const financialTrends = stages.financial_trends?.data;
    const valuation = stages.valuation?.data;
    const technicals = stages.technicals?.data;
    const riskManagement = stages.risk_management?.data;
    const sentiment = stages.sentiment?.data;
    const edgar = stages.edgar?.data;
    const thesis = stages.thesis?.data;

    const hasAnyData = Object.values(stages).some(s => s?.status === 'complete');

    return (
        <div className="fade-in">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">🧠 Deep Research</h1>
                    <p className="page-subtitle">Institutional-grade AI analysis with live streaming results</p>
                </div>
                {isStreaming && (
                    <button className="btn btn-danger" onClick={cancel}>
                        ⏹ Stop
                    </button>
                )}
            </div>

            {/* Search Bar */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xl)' }}>
                <input
                    ref={inputRef}
                    id="deep-research-input"
                    className="input"
                    placeholder="Enter any ticker (e.g. NVDA, AAPL, TSLA, QQQ)…"
                    value={ticker}
                    onChange={e => setTicker(e.target.value.toUpperCase())}
                    style={{ maxWidth: 360 }}
                    disabled={isStreaming}
                />
                <button
                    id="btn-deep-research"
                    className="btn btn-primary"
                    type="submit"
                    disabled={isStreaming || !ticker.trim()}
                >
                    {isStreaming ? (
                        <><span className="spinner spinner-sm" /> Researching…</>
                    ) : (
                        '🧠 Deep Research'
                    )}
                </button>
            </form>

            {error && (
                <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>
            )}

            {/* Timeline (always visible during/after streaming) */}
            {stageOrder.length > 0 && (
                <div style={{ marginBottom: 'var(--spacing-xl)' }}>
                    <ResearchTimeline stages={stages} stageOrder={stageOrder} />
                </div>
            )}

            {/* Report Header (shows once fundamentals are in) */}
            {fundamentals && !fundamentals.error && (
                <div className="glass-card fade-in" style={{ marginBottom: 'var(--spacing-lg)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <span className="ticker-badge" style={{ fontSize: '1rem', padding: '4px 14px' }}>
                                    {fundamentals.ticker}
                                </span>
                                <h2 style={{ fontSize: '1.1rem' }}>{fundamentals.company_name}</h2>
                            </div>
                            <div style={{ marginTop: 6, display: 'flex', gap: 8, alignItems: 'center' }}>
                                <span className="badge badge-blue">{fundamentals.sector}</span>
                                {fundamentals.is_etf && <span className="badge badge-purple">ETF</span>}
                                {pipelineInfo && (
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                        Report #{pipelineInfo.report_id?.slice(0, 8)}
                                    </span>
                                )}
                            </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '1.5rem', fontWeight: 700 }}>
                                ${fundamentals.current_price?.toFixed(2) ?? '—'}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                {fundamentals.pct_from_52w_high != null && (
                                    <span style={{ color: fundamentals.pct_from_52w_high >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                        {fundamentals.pct_from_52w_high >= 0 ? '+' : ''}{fundamentals.pct_from_52w_high}% from 52W high
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Streaming Results — each card appears as its stage completes */}
            {hasAnyData && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                    {/* Row 1: Fundamentals + Technicals side by side */}
                    {(fundamentals || technicals) && (
                        <div className="grid grid-2" style={{ gap: 'var(--spacing-lg)' }}>
                            {stages.fundamentals?.status === 'complete' && <FundamentalsCard fund={fundamentals} />}
                            {stages.technicals?.status === 'complete' && <TechnicalsCard tech={technicals} />}
                        </div>
                    )}

                    {/* Row 2: Financial Trends (full width) */}
                    {stages.financial_trends?.status === 'complete' && financialTrends && (
                        <FinancialTrendsChart trends={financialTrends} />
                    )}
                    
                    {/* Row 2.5: Valuation */}
                    {stages.valuation?.status === 'complete' && valuation && (
                        <ValuationCard valuation={valuation} />
                    )}
                    
                    {/* Row 2.75: Risk Management */}
                    {stages.risk_management?.status === 'complete' && riskManagement && (
                        <RiskCard riskData={riskManagement} />
                    )}

                    {/* Row 3: Sentiment */}
                    {stages.sentiment?.status === 'complete' && (
                        <SentimentMeter sentiment={sentiment} />
                    )}

                    {/* Row 4: SEC Filing */}
                    {stages.edgar?.status === 'complete' && edgar && !edgar.skipped && (
                        <EdgarCard edgar={edgar} />
                    )}

                    {/* Row 5: AI Thesis (the grand finale) */}
                    {stages.thesis?.status === 'complete' && (
                        <ThesisCard thesis={thesis} />
                    )}

                    {/* Report footer */}
                    {report && (
                        <div style={{
                            textAlign: 'center', padding: 'var(--spacing-md)',
                            fontSize: '0.72rem', color: 'var(--text-muted)'
                        }}>
                            ✅ Research complete · {report.total_llm_calls} AI calls · Report {report.report_id?.slice(0, 8)}
                        </div>
                    )}
                </div>
            )}

            {/* Empty state */}
            {!hasAnyData && !isStreaming && stageOrder.length === 0 && (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🧠</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>Enter a ticker to start deep research</h3>
                        <p style={{ fontSize: '0.825rem', maxWidth: 460, lineHeight: 1.7 }}>
                            Watch the AI analyze fundamentals, compute financial trajectories,
                            evaluate sentiment, read SEC filings, and generate an investment thesis
                            — all streamed live as each stage completes.
                        </p>
                        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                            {['NVDA', 'AAPL', 'TSLA', 'MSFT', 'KO'].map(t => (
                                <button key={t} className="btn btn-secondary" style={{ fontSize: '0.75rem' }}
                                    onClick={() => { setTicker(t); startResearch(t); }}>
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

import { useState } from 'react';
import { getResearchReport, compareTickers } from '../utils/api';

// ── Sentiment Meter ────────────────────────────────────────
function SentimentMeter({ sentiment }) {
    if (!sentiment) return null;
    const score = sentiment.composite_score ?? 5;
    const pct   = (score / 10) * 100;
    const label = sentiment.label || (score >= 6.5 ? 'bullish' : score <= 3.5 ? 'bearish' : 'neutral');
    const cls   = `sentiment-${label}`;

    return (
        <div style={{ marginBottom: 'var(--spacing-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Composite Sentiment</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>
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
                    { label: 'News (40%)',    val: sentiment.news_score },
                    { label: 'Analysts (35%)', val: sentiment.analyst_score, extra: sentiment.analyst_rating },
                    { label: 'Reddit (15%)',  val: sentiment.reddit_score, extra: `${sentiment.reddit_mentions ?? 0} mentions` },
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
        </div>
    );
}

// ── AI Thesis Card ─────────────────────────────────────────
function ThesisCard({ thesis }) {
    if (!thesis) return null;
    const recCls = {
        BUY: 'rec-buy', HOLD: 'rec-hold', TRIM: 'rec-trim', AVOID: 'rec-avoid'
    }[thesis.recommendation] || '';
    const convCls = {
        HIGH: 'conviction-high', MEDIUM: 'conviction-medium', LOW: 'conviction-low'
    }[thesis.conviction] || '';

    return (
        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
            {thesis.error ? (
                <div className="alert alert-warning">{thesis.summary}</div>
            ) : (
                <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-md)' }}>
                        <h3 style={{ fontSize: '0.925rem', color: 'var(--text-primary)' }}>🤖 AI Investment Thesis</h3>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <span className={`badge badge-${thesis.recommendation === 'BUY' ? 'green' : thesis.recommendation === 'HOLD' ? 'yellow' : 'red'}`}>
                                {thesis.recommendation}
                            </span>
                            <span className={`badge ${convCls}`} style={{ border: '1px solid' }}>
                                {thesis.conviction} conviction
                            </span>
                        </div>
                    </div>

                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: 1.7 }}>
                        {thesis.summary}
                    </p>

                    <div className="grid grid-2" style={{ gap: 'var(--spacing-md)' }}>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-green)', marginBottom: 8 }}>
                                Bull Case
                            </div>
                            {(thesis.bull_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-green)' }}>↑</span>{b}
                                </div>
                            ))}
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-red)', marginBottom: 8 }}>
                                Bear Case
                            </div>
                            {(thesis.bear_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-red)' }}>↓</span>{b}
                                </div>
                            ))}
                        </div>
                    </div>

                    {thesis.action_items?.length > 0 && (
                        <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-md)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-blue-bright)', marginBottom: 8 }}>
                                Action Items
                            </div>
                            {thesis.action_items.map((a, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0' }}>
                                    → {a}
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

// ── Fundamentals Tab ───────────────────────────────────────
function FundamentalsTab({ fund }) {
    if (!fund) return null;
    const rows = [
        ['Market Cap', fund.market_cap_fmt],
        ['Forward P/E', fund.forward_pe],
        ['Trailing P/E', fund.trailing_pe],
        ['EPS (TTM)', fund.eps != null ? `$${fund.eps}` : null],
        ['Price/Book', fund.price_to_book],
        ['Revenue (TTM)', fund.revenue_fmt],
        ['Revenue Growth', fund.revenue_growth != null ? `${fund.revenue_growth > 0 ? '+' : ''}${fund.revenue_growth.toFixed(1)}%` : null],
        ['Profit Margin', fund.profit_margin != null ? `${fund.profit_margin.toFixed(1)}%` : null],
        ['Gross Margin', fund.gross_margin != null ? `${fund.gross_margin.toFixed(1)}%` : null],
        ['Debt/Equity', fund.debt_to_equity],
        ['Current Ratio', fund.current_ratio],
        ['Beta', fund.beta],
        ['Dividend Yield', fund.dividend_yield != null ? `${fund.dividend_yield.toFixed(2)}%` : null],
        ['52W High', fund.week_52_high != null ? `$${fund.week_52_high}` : null],
        ['52W Low', fund.week_52_low != null ? `$${fund.week_52_low}` : null],
    ];

    return (
        <div className="grid grid-2" style={{ gap: 'var(--spacing-sm)' }}>
            {rows.filter(([, v]) => v != null && v !== 'N/A').map(([label, val]) => (
                <div key={label} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '8px 12px', background: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-sm)', fontSize: '0.8rem'
                }}>
                    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{String(val)}</span>
                </div>
            ))}
        </div>
    );
}

// ── Technicals Tab ─────────────────────────────────────────
function TechnicalsTab({ tech }) {
    if (!tech) return null;
    const rows = [
        ['RSI (14)', tech.rsi != null ? `${tech.rsi} — ${tech.rsi_signal}` : null],
        ['MACD Signal', tech.macd?.signal_label],
        ['50-Day MA', tech.ma_50 != null ? `$${tech.ma_50}` : null],
        ['200-Day MA', tech.ma_200 != null ? `$${tech.ma_200}` : null],
        ['Golden Cross', tech.golden_cross != null ? (tech.golden_cross ? '✅ Yes' : '❌ No') : null],
        ['Above 50-DMA', tech.above_50ma != null ? (tech.above_50ma ? '✅' : '❌') : null],
        ['Above 200-DMA', tech.above_200ma != null ? (tech.above_200ma ? '✅' : '❌') : null],
        ['1Y Return', tech.year_return_pct != null ? `${tech.year_return_pct > 0 ? '+' : ''}${tech.year_return_pct.toFixed(2)}%` : null],
        ['Volatility (Ann.)', tech.annualized_volatility_pct != null ? `${tech.annualized_volatility_pct.toFixed(1)}%` : null],
        ['Bollinger Position', tech.bollinger?.position != null ? tech.bollinger.position.toFixed(2) : null],
    ];

    return (
        <div>
            <div className="grid grid-2" style={{ gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-md)' }}>
                {rows.filter(([, v]) => v != null).map(([label, val]) => (
                    <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between',
                        padding: '8px 12px', background: 'var(--bg-secondary)',
                        borderRadius: 'var(--radius-sm)', fontSize: '0.8rem'
                    }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{val}</span>
                    </div>
                ))}
            </div>
            {tech.patterns?.length > 0 && (
                <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: 10 }}>
                        Detected Patterns
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
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

// ── SEC Filing Tab ─────────────────────────────────────────
function EdgarTab({ edgar }) {
    if (!edgar) return <div className="empty-state"><p>No SEC filing data</p></div>;
    if (!edgar.available) return (
        <div className="alert alert-warning">
            {edgar.error || 'SEC filing data unavailable for this ticker'}
        </div>
    );
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
            {edgar.filing_date && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    📄 {edgar.form_type} filed {edgar.filing_date}
                </div>
            )}
            {[
                { key: 'business', label: '🏢 Business Description' },
                { key: 'risks',    label: '⚠️ Key Risk Factors' },
                { key: 'mda',      label: '📈 Management Discussion & Analysis' },
            ].map(({ key, label }) => edgar[key] ? (
                <div key={key}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>{label}</div>
                    <div style={{
                        fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.8,
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

// ── Main Research Page ─────────────────────────────────────
export default function ResearchPage() {
    const [ticker, setTicker]   = useState('');
    const [report, setReport]   = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError]     = useState('');
    const [tab, setTab]         = useState('overview');

    // Comparison mode
    const [compareMode, setCompare] = useState(false);
    const [compareTickers_, setCompareTickers] = useState('');
    const [comparison, setComparison]          = useState(null);

    async function handleSearch(e) {
        e.preventDefault();
        if (!ticker.trim()) return;
        setLoading(true); setError(''); setReport(null); setTab('overview');
        try {
            const data = await getResearchReport(ticker.trim().toUpperCase(), { noEdgar: false });
            setReport(data);
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    async function handleCompare(e) {
        e.preventDefault();
        const tickers = compareTickers_.split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
        if (tickers.length < 2) { setError('Enter at least 2 tickers separated by commas'); return; }
        setLoading(true); setError(''); setComparison(null);
        try {
            const data = await compareTickers(tickers);
            setComparison(data);
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    }

    const tabs = [
        { id: 'overview',     label: '🎯 Overview' },
        { id: 'fundamentals', label: '📊 Fundamentals' },
        { id: 'technicals',   label: '📈 Technicals' },
        { id: 'sentiment',    label: '🌡️ Sentiment' },
        { id: 'edgar',        label: '📄 SEC Filings' },
    ];

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Research</h1>
                    <p className="page-subtitle">Deep AI-powered analysis for any US stock or ETF</p>
                </div>
                <button
                    id="btn-toggle-compare"
                    className={`btn ${compareMode ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => { setCompare(!compareMode); setComparison(null); setError(''); }}
                >
                    ⚖️ {compareMode ? 'Single Mode' : 'Compare Mode'}
                </button>
            </div>

            {/* Search */}
            {!compareMode ? (
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xl)' }}>
                    <input
                        id="research-ticker-input"
                        className="input"
                        placeholder="Enter ticker (e.g. NVDA, AAPL, QQQ)…"
                        value={ticker}
                        onChange={e => setTicker(e.target.value.toUpperCase())}
                        style={{ maxWidth: 320 }}
                    />
                    <button id="btn-research" className="btn btn-primary" type="submit" disabled={loading}>
                        {loading ? <><span className="spinner spinner-sm" /> Analyzing…</> : '🔬 Analyze'}
                    </button>
                    {report && (
                        <button type="button" className="btn btn-secondary"
                            onClick={() => { setLoading(true); getResearchReport(ticker, { refresh: true, noEdgar: false }).then(setReport).finally(() => setLoading(false)); }}>
                            🔄 Refresh
                        </button>
                    )}
                </form>
            ) : (
                <form onSubmit={handleCompare} style={{ display: 'flex', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-xl)' }}>
                    <input
                        id="compare-tickers-input"
                        className="input"
                        placeholder="Enter tickers separated by commas (e.g. NVDA, AMD, INTC)…"
                        value={compareTickers_}
                        onChange={e => setCompareTickers(e.target.value.toUpperCase())}
                        style={{ maxWidth: 460 }}
                    />
                    <button id="btn-compare" className="btn btn-primary" type="submit" disabled={loading}>
                        {loading ? <><span className="spinner spinner-sm" /> Comparing…</> : '⚖️ Compare'}
                    </button>
                </form>
            )}

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            {loading && (
                <div className="loading-state">
                    <div className="spinner" />
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ color: 'var(--text-secondary)' }}>Running deep analysis…</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                            Fetching SEC filings, sentiment signals, and generating AI thesis
                        </div>
                    </div>
                </div>
            )}

            {/* Single report */}
            {report && !loading && (
                <div>
                    {/* Header */}
                    <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <span className="ticker-badge" style={{ fontSize: '1rem', padding: '4px 12px' }}>{report.ticker}</span>
                                    <h2 style={{ fontSize: '1.1rem' }}>{report.company_name}</h2>
                                </div>
                                <div style={{ marginTop: 6, display: 'flex', gap: 8 }}>
                                    <span className="badge badge-blue">{report.sector}</span>
                                    {report.is_etf && <span className="badge badge-purple">ETF</span>}
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        Generated {new Date(report.generated_at).toLocaleTimeString()}
                                    </span>
                                </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontFamily: 'monospace', fontSize: '1.5rem', fontWeight: 700 }}>
                                    ${report.fundamentals?.current_price?.toFixed(2) ?? '—'}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current Price</div>
                            </div>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="tabs" style={{ marginBottom: 'var(--spacing-lg)' }}>
                        {tabs.map(t => (
                            <button key={t.id} id={`tab-${t.id}`}
                                className={`tab-btn ${tab === t.id ? 'active' : ''}`}
                                onClick={() => setTab(t.id)}>
                                {t.label}
                            </button>
                        ))}
                    </div>

                    {/* Tab content */}
                    {tab === 'overview' && (
                        <>
                            <ThesisCard thesis={report.thesis} />
                            <SentimentMeter sentiment={report.sentiment} />
                        </>
                    )}
                    {tab === 'fundamentals' && (
                        <div className="glass-card"><FundamentalsTab fund={report.fundamentals} /></div>
                    )}
                    {tab === 'technicals' && (
                        <div className="glass-card"><TechnicalsTab tech={report.technicals} /></div>
                    )}
                    {tab === 'sentiment' && (
                        <div className="glass-card"><SentimentMeter sentiment={report.sentiment} /></div>
                    )}
                    {tab === 'edgar' && (
                        <div className="glass-card"><EdgarTab edgar={report.edgar_summary} /></div>
                    )}
                </div>
            )}

            {/* Comparison view */}
            {comparison && !loading && (
                <div>
                    {comparison.comparison && !comparison.comparison.error && (
                        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)' }}>
                            <div className="card-header">
                                <span className="card-title">AI Comparison</span>
                                {comparison.comparison.winner && (
                                    <span className="badge badge-green">Winner: {comparison.comparison.winner}</span>
                                )}
                            </div>
                            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                {comparison.comparison.summary}
                            </p>
                            {comparison.comparison.ranking && (
                                <div style={{ display: 'flex', gap: 8, marginTop: 'var(--spacing-md)' }}>
                                    {comparison.comparison.ranking.map((t, i) => (
                                        <span key={t} className={`badge ${i === 0 ? 'badge-green' : i === 1 ? 'badge-yellow' : 'badge-gray'}`}>
                                            #{i + 1} {t}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    <div className={`grid grid-${Math.min(comparison.reports?.length, 2)}`}>
                        {(comparison.reports || []).map(r => (
                            <div key={r.ticker} className="glass-card">
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--spacing-md)' }}>
                                    <div>
                                        <span className="ticker-badge">{r.ticker}</span>
                                        <span style={{ marginLeft: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{r.company_name}</span>
                                    </div>
                                    <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>
                                        ${r.fundamentals?.current_price?.toFixed(2) ?? '—'}
                                    </span>
                                </div>
                                {r.thesis && (
                                    <>
                                        <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                                            <span className={`badge badge-${r.thesis.recommendation === 'BUY' ? 'green' : r.thesis.recommendation === 'HOLD' ? 'yellow' : 'red'}`}>
                                                {r.thesis.recommendation}
                                            </span>
                                            <span className="badge badge-gray">{r.thesis.conviction} conviction</span>
                                        </div>
                                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{r.thesis.summary}</p>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!report && !comparison && !loading && (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🔬</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>Enter a ticker to start deep research</h3>
                        <p style={{ fontSize: '0.825rem', maxWidth: 400 }}>
                            Get fundamentals, technical signals, sentiment scoring, SEC filing summaries,
                            and an AI-generated investment thesis in one click.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

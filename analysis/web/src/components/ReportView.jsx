import React from 'react';
import RecommendationPill from './RecommendationPill';
import TradePlanCard from './TradePlanCard';
import ThesisGlance from './ThesisGlance';
import ChangeMyMindPanel from './ChangeMyMindPanel';
import CatalystsPanel from './CatalystsPanel';
import EvidenceLedger from './EvidenceLedger';
import FullDebate from './FullDebate';
import MemoDeltaPanel from './MemoDeltaPanel';

/**
 * ReportView — the polished post-stream report view for deep research.
 * Used by both DeepResearchPage (mode="live") and ResearchHistoryPage (mode="archived").
 *
 * @param {{ report: object, mode: 'live'|'archived', drift?: object, telemetry?: object }} props
 */
export default function ReportView({ report, mode = 'live', drift, telemetry }) {
    if (!report) return null;

    const verdict = report.verdict || {};
    const tradePlan = verdict.trade_plan || {};
    const bullThesis = report.bull_thesis || {};
    const bearThesis = report.bear_thesis || {};
    const evidence = report.evidence || {};
    const critique = report.self_critique || {};
    const memoDelta = report.memo_delta;
    const sector = report.sector || {};

    // Legacy quick-research fallback
    if (report.version !== 'deep' && report.version !== 'v2' && !verdict.recommendation) {
        return (
            <div className="glass-card" style={{ padding: 'var(--spacing-lg)', textAlign: 'center' }}>
                <div style={{ fontSize: '1.2rem', marginBottom: 8 }}>📄 Legacy Research Report</div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    This is a legacy archived report. Detailed analysis and views are optimized for agentic deep research v2 reports.
                </p>
            </div>
        );
    }

    const currentPrice = drift?.current_price || report.price_at_report || 0;

    return (
        <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
            {/* ── EXECUTIVE HEADER ── */}
            <div className="glass-card" style={{ borderColor: 'rgba(45, 126, 247, 0.3)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                            <span className="ticker-badge" style={{ fontSize: '1.2rem', padding: '6px 16px' }}>
                                {report.ticker}
                            </span>
                            {sector.sector_key && (
                                <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>{sector.sector_key}</span>
                            )}
                            {mode === 'archived' && (
                                <span className="badge badge-gray" style={{ fontSize: '0.65rem' }}>Archived</span>
                            )}
                        </div>
                        <RecommendationPill recommendation={verdict.recommendation} conviction={verdict.conviction} />
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        {verdict.target_price_range && (
                            <div style={{ marginBottom: 6 }}>
                                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Target: </span>
                                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.9rem', color: 'var(--accent-green)' }}>
                                    ${verdict.target_price_range.low} — ${verdict.target_price_range.high}
                                </span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 6 }}>
                                    ({verdict.target_price_range.timeframe})
                                </span>
                            </div>
                        )}
                        {drift && drift.price_at_report > 0 && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                Price at report: <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>${drift.price_at_report.toFixed(2)}</span>
                                {' → '}
                                <span style={{ fontFamily: "'JetBrains Mono', monospace", color: drift.pct_change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                    ${drift.current_price.toFixed(2)} ({drift.pct_change >= 0 ? '+' : ''}{drift.pct_change}%)
                                </span>
                                <span style={{ marginLeft: 6 }}>{drift.days_old}d ago</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Summary */}
                {verdict.summary && (
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 12 }}>
                        {verdict.summary}
                    </p>
                )}

                {/* Telemetry bar */}
                <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {telemetry?.evidence_tool_count != null && <span>✅ {telemetry.evidence_tool_count} tools</span>}
                    {telemetry?.total_llm_calls != null && telemetry.total_llm_calls > 0 && <span>🧠 {telemetry.total_llm_calls} LLM calls</span>}
                    {telemetry?.cost_used_usd != null && telemetry.cost_used_usd > 0 && (
                        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>${telemetry.cost_used_usd.toFixed(3)}</span>
                    )}
                    {telemetry?.wall_clock_sec != null && <span>{telemetry.wall_clock_sec}s</span>}
                    {report.tracked_for_calibration && <span className="badge badge-green" style={{ fontSize: '0.6rem' }}>tracked</span>}
                </div>
            </div>

            {/* ── TRADE PLAN ── */}
            <TradePlanCard plan={tradePlan} currentPrice={currentPrice} />

            {/* ── THESIS AT A GLANCE ── */}
            <ThesisGlance bullCase={verdict.bull_case} bearCase={verdict.bear_case} />

            {/* ── WHAT WOULD CHANGE MY MIND ── */}
            <ChangeMyMindPanel items={verdict.what_would_change_mind} />

            {/* ── KEY CATALYSTS ── */}
            <CatalystsPanel items={verdict.key_catalysts} />

            {/* ── EVIDENCE LEDGER ── */}
            <EvidenceLedger results={evidence.results || []} />

            {/* ── FULL DEBATE ── */}
            <FullDebate bull={bullThesis} bear={bearThesis} verdict={verdict} />

            {/* ── SELF-CRITIQUE ── */}
            {critique?.weakest_claims?.length > 0 && (
                <details className="glass-card" style={{ padding: 'var(--spacing-md)' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}>
                         🔍 Self-Critique: {critique.weakest_claims.length} weak claim(s)
                        {critique.should_revise_verdict && ' — revision suggested'}
                    </summary>
                    <div style={{ marginTop: 10 }}>
                        {critique.weakest_claims.map((c, i) => (
                            <div key={i} style={{ padding: '6px 0', fontSize: '0.78rem', borderBottom: '1px solid var(--border-color)' }}>
                                <div><strong>{c.claim}</strong></div>
                                <div style={{ color: 'var(--text-muted)' }}>Why weak: {c.why_weak}</div>
                                <div style={{ color: 'var(--text-muted)' }}>Falsified by: {c.would_be_falsified_by}</div>
                            </div>
                        ))}
                        {critique.revision_suggestion && (
                            <div style={{ marginTop: 8, fontSize: '0.78rem' }}>
                                <strong>Suggested revision:</strong> {critique.revision_suggestion}
                            </div>
                        )}
                    </div>
                </details>
            )}

            {/* ── LIVING MEMO DELTA ── */}
            <MemoDeltaPanel delta={memoDelta} />

            {/* ── FOOTER ── */}
            <div style={{ textAlign: 'center', padding: 'var(--spacing-sm)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                Report ID: <code>{report.report_id}</code>
                {report.budget_used && (
                    <span> · Budget: {report.budget_profile}</span>
                )}
            </div>
        </div>
    );
}

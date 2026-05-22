import React, { useState, useRef, useCallback } from 'react';
import { streamDeepResearch } from '../utils/api';
import ReportView from '../components/ReportView';
import StageTimeline from '../components/StageTimeline';

/**
 * Deep Research — agentic loop + multi-agent debate + Living Memo.
 *
 * Shows a stage timeline during streaming, a collapsible activity
 * drawer for transparency, and the polished ReportView on completion.
 */

export default function DeepResearchPage() {
    const [ticker, setTicker] = useState('');
    const [budget, setBudget] = useState('normal');
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState(null);
    const [reportId, setReportId] = useState(null);
    const [sectorInfo, setSectorInfo] = useState(null);
    const [plans, setPlans] = useState([]);
    const [toolCalls, setToolCalls] = useState([]);
    const [debateTurns, setDebateTurns] = useState({});
    const [verdict, setVerdict] = useState(null);
    const [critique, setCritique] = useState(null);
    const [memoDelta, setMemoDelta] = useState(null);
    const [reportComplete, setReportComplete] = useState(null);
    const [fullReport, setFullReport] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(true);
    const [stageStatuses, setStageStatuses] = useState({});
    const closeRef = useRef(null);

    const updateStage = useCallback((key, status) => {
        setStageStatuses(prev => ({ ...prev, [key]: status }));
    }, []);

    const reset = useCallback(() => {
        setError(null); setReportId(null); setSectorInfo(null); setPlans([]);
        setToolCalls([]); setDebateTurns({}); setVerdict(null); setCritique(null);
        setMemoDelta(null); setReportComplete(null); setFullReport(null);
        setDrawerOpen(true); setStageStatuses({});
    }, []);

    const start = useCallback(() => {
        const t = ticker.trim().toUpperCase();
        if (!t) return;
        reset();
        setIsStreaming(true);

        const close = streamDeepResearch(t, {
            onPipelineStart: (d) => {
                setReportId(d.report_id);
            },
            onContextLoaded: (d) => {
                setSectorInfo(d);
                updateStage('context', 'complete');
                updateStage('plan', 'active');
            },
            onAgentPlan: (d) => {
                setPlans(prev => [...prev, d]);
                updateStage('plan', d.done ? 'complete' : 'active');
                if (!d.done && d.next_calls?.length > 0) {
                    updateStage('tools', 'active');
                }
            },
            onToolCallStart: () => {
                updateStage('tools', 'active');
            },
            onToolCallComplete: (d) => {
                setToolCalls(prev => [...prev, d]);
            },
            onToolCallError: (d) => {
                setToolCalls(prev => [...prev, { ...d, error: d.error }]);
            },
            onDebateStart: (d) => {
                updateStage('tools', 'complete');
                if (d.phase === 'bull') updateStage('bull', 'active');
                else if (d.phase === 'bear') updateStage('bear', 'active');
                else if (d.phase === 'judge') updateStage('judge', 'active');
            },
            onDebateTurn: (d) => {
                setDebateTurns(prev => ({ ...prev, [d.agent]: d.output }));
                if (d.agent === 'bull') { updateStage('bull', 'complete'); updateStage('bear', 'active'); }
                if (d.agent === 'bear') { updateStage('bear', 'complete'); }
            },
            onDebateComplete: (d) => {
                setVerdict(d.verdict);
                updateStage('judge', 'complete');
                updateStage('critique', 'active');
            },
            onSelfCritiqueStart: () => {
                updateStage('critique', 'active');
            },
            onSelfCritique: (d) => {
                setCritique(d);
                updateStage('critique', 'complete');
                updateStage('memo', 'active');
            },
            onMemoDeltaProposed: (d) => {
                setMemoDelta(d);
                updateStage('memo', 'complete');
            },
            onBudgetWarning: (d) => console.warn('Budget warning:', d),
            onReportComplete: (d) => {
                setReportComplete(d);
                updateStage('done', 'complete');
                setDrawerOpen(false);
                setIsStreaming(false);
                // Assemble the full report from streamed data
                setFullReport({
                    report_id: d.report_id,
                    ticker: d.ticker,
                    version: 'deep',
                    verdict: null, // will be set from state
                    bull_thesis: null,
                    bear_thesis: null,
                    evidence: { results: [] },
                    self_critique: null,
                    memo_delta: null,
                });
            },
            onError: (d) => { setError(d.error || 'stream error'); setIsStreaming(false); },
        }, { budget });
        closeRef.current = close;
    }, [ticker, budget, reset, updateStage]);

    const cancel = useCallback(() => {
        closeRef.current?.();
        setIsStreaming(false);
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        start();
    };

    // Build the report object from streamed state for ReportView
    const assembledReport = reportComplete ? {
        report_id: reportComplete.report_id,
        ticker: reportComplete.ticker,
        version: 'deep',
        verdict: verdict || {},
        bull_thesis: debateTurns.bull || {},
        bear_thesis: debateTurns.bear || {},
        evidence: { results: toolCalls.filter(c => !c.error) },
        self_critique: critique || {},
        memo_delta: memoDelta,
        sector: sectorInfo || {},
        tracked_for_calibration: true,
        price_at_report: 0,
    } : null;

    const telemetry = reportComplete ? {
        evidence_tool_count: reportComplete.evidence_tool_count,
        cost_used_usd: reportComplete.cost_used_usd,
        wall_clock_sec: reportComplete.wall_clock_sec,
        total_llm_calls: reportComplete.total_llm_calls,
    } : null;

    const toolsCompleted = toolCalls.length;
    const toolsErrored = toolCalls.filter(c => c.error).length;

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">🧠 Deep Research</h1>
                    <p className="page-subtitle">Agentic loop · Bull/Bear/Judge debate · Living Memo · Citation-first</p>
                </div>
                {isStreaming && <button className="btn btn-danger" onClick={cancel}>⏹ Stop</button>}
            </div>

            {/* ── Input Form ── */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, marginBottom: 'var(--spacing-xl)', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                    id="deep-research-input"
                    className="input"
                    placeholder="Enter ticker (e.g. NVDA)…"
                    value={ticker}
                    onChange={e => setTicker(e.target.value.toUpperCase())}
                    style={{ maxWidth: 280 }}
                    disabled={isStreaming}
                />
                <select
                    id="budget-profile"
                    className="input"
                    value={budget}
                    onChange={e => setBudget(e.target.value)}
                    disabled={isStreaming}
                    style={{ maxWidth: 180 }}
                >
                    <option value="quick">Quick (~$0.10)</option>
                    <option value="normal">Normal (~$0.60)</option>
                    <option value="deep">Deep (~$2.00)</option>
                </select>
                <button id="btn-deep-research" className="btn btn-primary" type="submit" disabled={isStreaming || !ticker.trim()}>
                    {isStreaming ? <><span className="spinner spinner-sm" /> Researching…</> : '🚀 Research'}
                </button>
            </form>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            {/* ── Stage Timeline (visible during and after streaming) ── */}
            {(isStreaming || reportComplete) && (
                <StageTimeline
                    stageStatuses={stageStatuses}
                    toolProgress={isStreaming ? `${toolsCompleted}${toolsErrored > 0 ? ` · ${toolsErrored} err` : ''}` : null}
                />
            )}

            {/* ── Report View (shown after completion) ── */}
            {assembledReport && (
                <ReportView report={assembledReport} mode="live" telemetry={telemetry} />
            )}

            {/* ── Collapsible Activity Drawer ── */}
            {(isStreaming || reportComplete) && (
                <details open={drawerOpen} style={{ marginTop: 'var(--spacing-lg)' }}
                    onToggle={(e) => setDrawerOpen(e.target.open)}>
                    <summary style={{
                        cursor: 'pointer', fontWeight: 600, fontSize: '0.82rem',
                        color: 'var(--text-secondary)', padding: '8px 0', outline: 'none',
                    }}>
                        {isStreaming ? '🔄' : '📋'} Live Activity
                        ({plans.length} plan{plans.length !== 1 ? 's' : ''} · {toolsCompleted} tool{toolsCompleted !== 1 ? 's' : ''}{toolsErrored > 0 ? ` · ${toolsErrored} error${toolsErrored !== 1 ? 's' : ''}` : ''})
                    </summary>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-md)' }}>
                        {/* Sector context */}
                        {sectorInfo && (
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                                <span className="badge badge-blue" style={{ fontSize: '0.72rem' }}>Sector: {sectorInfo.sector_key}</span>
                                {sectorInfo.memo_version > 0 && <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>Memo v{sectorInfo.memo_version}</span>}
                            </div>
                        )}

                        {/* Plans */}
                        {plans.map((p, i) => (
                            <div key={`plan-${i}`} className="glass-card fade-in" style={{ padding: 12, background: 'rgba(124,58,237,0.08)', borderColor: 'rgba(124,58,237,0.25)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                    <strong style={{ color: 'var(--accent-purple)', fontSize: '0.8rem' }}>📋 Planner round {i + 1}</strong>
                                    {p.done && <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>done</span>}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{p.summary}</div>
                                {p.next_calls?.length > 0 && (
                                    <div style={{ fontSize: '0.72rem', marginTop: 4 }}>
                                        {p.next_calls.map((c, j) => (
                                            <div key={j} style={{ padding: '2px 0' }}>
                                                 → <code>{c.tool}</code>: <span style={{ color: 'var(--text-muted)' }}>{c.reason}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Tool calls grid */}
                        {toolCalls.length > 0 && (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
                                {toolCalls.map((c, i) => (
                                    <div key={`tc-${i}`} className="glass-card fade-in" style={{
                                        padding: 10, borderLeft: `3px solid ${c.error ? 'var(--accent-red)' : 'var(--accent-green)'}`,
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <code style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-blue-bright)' }}>{c.tool}</code>
                                            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{c.latency_ms}ms</span>
                                        </div>
                                        {c.error && <div style={{ fontSize: '0.72rem', color: 'var(--accent-red)', marginTop: 4 }}>{c.error}</div>}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Debate turns (raw) */}
                        {debateTurns.bull && (
                            <div style={{ padding: 10, borderLeft: '3px solid var(--accent-green)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                <strong style={{ color: 'var(--accent-green)' }}>🐂 Bull</strong>
                                <div style={{ marginTop: 4, whiteSpace: 'pre-line', maxHeight: 120, overflow: 'hidden' }}>{debateTurns.bull.thesis_md?.slice(0, 300)}…</div>
                            </div>
                        )}
                        {debateTurns.bear && (
                            <div style={{ padding: 10, borderLeft: '3px solid var(--accent-red)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                <strong style={{ color: 'var(--accent-red)' }}>🐻 Bear</strong>
                                <div style={{ marginTop: 4, whiteSpace: 'pre-line', maxHeight: 120, overflow: 'hidden' }}>{debateTurns.bear.attack_md?.slice(0, 300)}…</div>
                            </div>
                        )}
                    </div>
                </details>
            )}

            {/* ── Empty state ── */}
            {!isStreaming && !reportId && (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🧠</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>Living Analyst</h3>
                        <p style={{ fontSize: '0.825rem', maxWidth: 480, lineHeight: 1.7 }}>
                            Agentic loop with multi-agent debate, per-ticker Living Memo, citation-first.
                            Each session reads the prior memo, identifies what's stale, investigates, and refines it.
                        </p>
                        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                            {['NVDA', 'AAPL', 'MSFT', 'JPM', 'XOM'].map(t => (
                                <button key={t} className="btn btn-secondary" style={{ fontSize: '0.75rem' }}
                                    onClick={() => { setTicker(t); }}>{t}</button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

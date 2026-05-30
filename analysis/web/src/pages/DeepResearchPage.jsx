import React, { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
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
    const [budget, setBudget] = useState('deep');
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
    const [activeToolDetail, setActiveToolDetail] = useState(null);
    const closeRef = useRef(null);

    const updateStage = useCallback((key, status) => {
        setStageStatuses(prev => ({ ...prev, [key]: status }));
    }, []);

    const reset = useCallback(() => {
        setError(null); setReportId(null); setSectorInfo(null); setPlans([]);
        setToolCalls([]); setDebateTurns({}); setVerdict(null); setCritique(null);
        setMemoDelta(null); setReportComplete(null); setFullReport(null);
        setDrawerOpen(true); setStageStatuses({}); setActiveToolDetail(null);
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
                    <h1 className="page-title">Deep Research</h1>
                    <p className="page-subtitle">Agentic loop · Bull/Bear/Judge debate · Living Memo · Citation-first</p>
                </div>
                {isStreaming && <button className="btn btn-danger" onClick={cancel}>Stop</button>}
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
                <button id="btn-deep-research" className="btn btn-primary" type="submit" disabled={isStreaming || !ticker.trim()}>
                    {isStreaming ? <><span className="spinner spinner-sm" /> Researching…</> : 'Research'}
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
                        Live Activity
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

                        {/* Tool calls grid */}
                        {toolCalls.length > 0 && (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
                                {toolCalls.map((c, i) => (
                                    <div key={`tc-${i}`} 
                                        className="glass-card fade-in" 
                                        onClick={() => setActiveToolDetail(c)}
                                        style={{
                                            padding: 12, 
                                            borderLeft: `3px solid ${c.error ? 'var(--accent-red)' : 'var(--accent-green)'}`,
                                            cursor: 'pointer',
                                            transition: 'transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease',
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-2px)';
                                            e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.03)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.backgroundColor = 'var(--bg-card)';
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <code style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-blue-bright)' }}>{c.tool}</code>
                                            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{c.latency_ms}ms</span>
                                        </div>
                                        {c.error ? (
                                            <div style={{ fontSize: '0.72rem', color: 'var(--accent-red)', marginTop: 4 }}>{c.error}</div>
                                        ) : (
                                            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                                Click to view {c.data ? 'extracted data' : 'details'}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Debate turns (raw) */}
                        {debateTurns.bull && (
                            <div style={{ padding: 10, borderLeft: '3px solid var(--accent-green)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                <strong style={{ color: 'var(--accent-green)' }}>Bull</strong>
                                <div style={{ marginTop: 4, whiteSpace: 'pre-line', maxHeight: 120, overflow: 'hidden' }}>{debateTurns.bull.thesis_md?.slice(0, 300)}…</div>
                            </div>
                        )}
                        {debateTurns.bear && (
                            <div style={{ padding: 10, borderLeft: '3px solid var(--accent-red)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                <strong style={{ color: 'var(--accent-red)' }}>Bear</strong>
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
                        <div className="empty-state-icon"></div>
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
            {/* ── Tool Data Viewer Modal ── */}
            {activeToolDetail && createPortal(
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.75)',
                    backdropFilter: 'blur(8px)',
                    zIndex: 2000,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    padding: 'var(--spacing-lg)',
                }} onClick={() => setActiveToolDetail(null)}>
                    <div style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-lg)',
                        width: '100%',
                        maxWidth: '720px',
                        maxHeight: '80vh',
                        display: 'grid',
                        gridTemplateRows: 'auto 1fr',
                        boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
                        overflow: 'hidden',
                    }} onClick={e => e.stopPropagation()}>
                        
                        {/* Header */}
                        <div style={{
                            padding: 'var(--spacing-md) var(--spacing-lg)',
                            borderBottom: '1px solid var(--border-color)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                        }}>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <code style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-blue-bright)' }}>
                                        {activeToolDetail.tool}
                                    </code>
                                    <span className={`badge ${activeToolDetail.error ? 'badge-red' : 'badge-green'}`} style={{ fontSize: '0.68rem' }}>
                                        {activeToolDetail.error ? 'Failed' : 'Success'}
                                    </span>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                    Execution time: {activeToolDetail.latency_ms}ms {activeToolDetail.confidence && `· Confidence: ${activeToolDetail.confidence}`}
                                </div>
                            </div>
                            <button className="btn btn-secondary" 
                                style={{ padding: '4px 12px', minWidth: 'auto', fontSize: '0.8rem' }}
                                onClick={() => setActiveToolDetail(null)}>
                                Close
                            </button>
                        </div>

                        {/* Content */}
                        <div style={{
                            padding: 'var(--spacing-lg)',
                            overflowY: 'auto',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 'var(--spacing-md)',
                            flex: 1,
                            minHeight: 0,
                        }}>
                            {activeToolDetail.error ? (
                                <div style={{ 
                                    padding: 'var(--spacing-md)', 
                                    background: 'rgba(239, 68, 68, 0.1)', 
                                    border: '1px solid rgba(239, 68, 68, 0.2)',
                                    borderRadius: 'var(--radius-md)',
                                    color: 'var(--accent-red)',
                                    fontSize: '0.825rem',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {activeToolDetail.error}
                                </div>
                            ) : (
                                <>
                                    {/* Extracted Data Fields */}
                                    <div>
                                        <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-sm)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Extracted Data
                                        </h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                                            {activeToolDetail.data && Object.keys(activeToolDetail.data).length > 0 ? (
                                                Object.entries(activeToolDetail.data).map(([key, val]) => {
                                                    const formatValue = (v) => {
                                                        if (typeof v === 'object' && v !== null) {
                                                            return (
                                                                <pre style={{
                                                                    margin: '6px 0 0 0',
                                                                    padding: '12px',
                                                                    background: 'rgba(0,0,0,0.25)',
                                                                    borderRadius: 'var(--radius-md)',
                                                                    fontFamily: 'var(--font-mono)',
                                                                    fontSize: '0.75rem',
                                                                    overflowX: 'auto',
                                                                    color: '#34d399',
                                                                    border: '1px solid rgba(255,255,255,0.05)',
                                                                    lineHeight: 1.5
                                                                }}>{JSON.stringify(v, null, 2)}</pre>
                                                            );
                                                        }
                                                        if (typeof v === 'boolean') return v ? '✅ True' : '❌ False';
                                                        if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
                                                        return String(v);
                                                    };

                                                    return (
                                                        <div key={key} style={{
                                                            borderBottom: '1px solid rgba(255,255,255,0.04)',
                                                            paddingBottom: 'var(--spacing-sm)',
                                                            display: 'flex',
                                                            flexDirection: 'column',
                                                            gap: 4
                                                        }}>
                                                            <span style={{
                                                                fontSize: '0.72rem',
                                                                fontWeight: 600,
                                                                color: 'var(--text-muted)',
                                                                textTransform: 'uppercase',
                                                                letterSpacing: '0.05em'
                                                            }}>{key.replace(/_/g, ' ')}</span>
                                                            <div style={{ fontSize: '0.825rem', color: 'var(--text-primary)', wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
                                                                {formatValue(val)}
                                                            </div>
                                                        </div>
                                                    );
                                                })
                                            ) : (
                                                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.8rem' }}>
                                                    No structured fields extracted.
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Sources */}
                                    {activeToolDetail.sources && activeToolDetail.sources.length > 0 && (
                                        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 'var(--spacing-md)', marginTop: 'var(--spacing-sm)' }}>
                                            <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-sm)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                Sources & Citations ({activeToolDetail.sources.length})
                                            </h4>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                                                {activeToolDetail.sources.map((s, idx) => (
                                                    <div key={idx} style={{
                                                        background: 'rgba(255,255,255,0.01)',
                                                        padding: '10px 14px',
                                                        borderRadius: 'var(--radius-md)',
                                                        border: '1px solid rgba(255,255,255,0.04)'
                                                    }}>
                                                        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-blue-bright)' }}>
                                                            {s.title || s.name || (s.tool ? `${s.tool}${s.field ? ` · ${s.field}` : ''}` : 'Source Reference')}
                                                        </div>
                                                        {s.url && (
                                                            <a href={s.url} target="_blank" rel="noreferrer" 
                                                                style={{ fontSize: '0.7rem', color: 'var(--accent-blue-bright)', textDecoration: 'underline', display: 'inline-block', marginTop: 2 }}>
                                                                {s.url}
                                                            </a>
                                                        )}
                                                        {(s.note || s.snippet) && (
                                                            <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: 6, fontStyle: 'italic', lineHeight: 1.45 }}>
                                                                "{s.note || s.snippet}"
                                                            </p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}

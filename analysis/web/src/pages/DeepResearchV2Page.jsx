import React, { useState, useRef, useCallback } from 'react';
import { streamDeepResearchV2, getCalibrationDashboard } from '../utils/api';

/**
 * Deep Research v2 — agentic loop + multi-agent debate + Living Memo.
 *
 * UI shows the live planner→tool→debate→verdict pipeline as it streams.
 * Sources are click-to-inspect; the Memo diff is shown when proposed.
 */

const RECOMMENDATION_COLORS = {
    BUY: 'green', HOLD: 'yellow', TRIM: 'orange', AVOID: 'red',
};
const CONVICTION_COLORS = { HIGH: 'green', MEDIUM: 'yellow', LOW: 'gray' };


function ToolCallCard({ call }) {
    const ok = !call.error;
    const sources = call.sources || [];
    const dataKeys = call.data_keys || Object.keys(call.data || {});
    return (
        <div className="glass-card fade-in" style={{ padding: 12, borderLeft: `3px solid ${ok ? 'var(--accent-green)' : 'var(--accent-red)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <code style={{ fontWeight: 700, color: 'var(--accent-blue-bright)' }}>{call.tool}</code>
                    <span className={`badge badge-${call.confidence === 'high' ? 'green' : call.confidence === 'medium' ? 'yellow' : 'gray'}`}
                          style={{ fontSize: '0.65rem' }}>{call.confidence}</span>
                    {call.cached && <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>cached</span>}
                </div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{call.latency_ms}ms</span>
            </div>
            {ok ? (
                <details>
                    <summary style={{ cursor: 'pointer', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {dataKeys.length} fields · {sources.length} source{sources.length === 1 ? '' : 's'}
                    </summary>
                    <pre style={{ fontSize: '0.7rem', maxHeight: 200, overflow: 'auto', background: 'var(--bg-secondary)', padding: 8, borderRadius: 4, marginTop: 8 }}>
                        {JSON.stringify(call.data, null, 2)}
                    </pre>
                    {sources.length > 0 && (
                        <div style={{ marginTop: 6, fontSize: '0.7rem' }}>
                            {sources.slice(0, 5).map((s, i) => (
                                <div key={i} style={{ color: 'var(--text-muted)' }}>
                                    📎 {s.tool}:{s.field}{s.url ? ` — ${s.url}` : ''}
                                </div>
                            ))}
                        </div>
                    )}
                </details>
            ) : (
                <div className="alert alert-warning" style={{ fontSize: '0.75rem', marginTop: 4 }}>{call.error}</div>
            )}
        </div>
    );
}


function AgentPlanCard({ plan, iteration }) {
    return (
        <div className="glass-card fade-in" style={{ padding: 12, background: 'rgba(124,58,237,0.08)', borderColor: 'rgba(124,58,237,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <strong style={{ color: 'var(--accent-purple)' }}>📋 Planner round {iteration + 1}</strong>
                {plan.done && <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>done</span>}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>{plan.summary}</div>
            {plan.next_calls?.length > 0 && (
                <div style={{ fontSize: '0.72rem' }}>
                    {plan.next_calls.map((c, i) => (
                        <div key={i} style={{ padding: '3px 0' }}>
                            → <code>{c.tool}</code>: <span style={{ color: 'var(--text-muted)' }}>{c.reason}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}


function DebateCard({ agent, output }) {
    const colors = { bull: 'green', bear: 'red', judge: 'blue' };
    const icons = { bull: '🐂', bear: '🐻', judge: '⚖️' };
    const color = colors[agent] || 'gray';
    return (
        <div className="glass-card fade-in" style={{ padding: 14, borderLeft: `3px solid var(--accent-${color})` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <strong style={{ textTransform: 'uppercase', fontSize: '0.85rem', color: `var(--accent-${color})` }}>
                    {icons[agent]} {agent}
                </strong>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                {output.thesis_md || output.attack_md || ''}
            </div>
            {output.independent_bear_md && (
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border-color)', fontSize: '0.8rem', whiteSpace: 'pre-line' }}>
                    <strong style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Independent bear case</strong>
                    <div style={{ marginTop: 6 }}>{output.independent_bear_md}</div>
                </div>
            )}
            {output.key_drivers && (
                <div style={{ marginTop: 10 }}>
                    {output.key_drivers.map((d, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', padding: '3px 0' }}>
                            ✓ {d.claim} <span style={{ color: 'var(--text-muted)' }}>[{(d.evidence_refs || []).join(', ')}]</span>
                        </div>
                    ))}
                </div>
            )}
            {output.key_risks && (
                <div style={{ marginTop: 10 }}>
                    {output.key_risks.map((r, i) => (
                        <div key={i} style={{ fontSize: '0.75rem', padding: '3px 0' }}>
                            ⚠ {r.risk} <span className={`badge badge-${r.severity === 'high' ? 'red' : 'yellow'}`} style={{ fontSize: '0.6rem', marginLeft: 4 }}>{r.severity}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}


function VerdictCard({ verdict }) {
    if (!verdict) return null;
    const rec = verdict.recommendation || 'HOLD';
    const conv = verdict.conviction || 'LOW';
    return (
        <div className="glass-card fade-in" style={{ borderColor: 'rgba(45,126,247,0.4)', padding: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <h3 style={{ fontSize: '1rem' }}>⚖️ Judge Verdict</h3>
                <div style={{ display: 'flex', gap: 8 }}>
                    <span className={`badge badge-${RECOMMENDATION_COLORS[rec] || 'gray'}`} style={{ fontSize: '0.85rem', padding: '4px 14px', fontWeight: 700 }}>{rec}</span>
                    <span className={`badge badge-${CONVICTION_COLORS[conv] || 'gray'}`} style={{ fontSize: '0.75rem', border: '1px solid' }}>{conv} conviction</span>
                </div>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 12 }}>{verdict.summary}</p>

            {verdict.what_would_change_mind?.length > 0 && (
                <div style={{ padding: 12, background: 'rgba(245,158,11,0.1)', borderRadius: 8, marginBottom: 12, border: '1px solid rgba(245,158,11,0.25)' }}>
                    <strong style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--accent-yellow, #f59e0b)', letterSpacing: '0.05em' }}>⚠️ What would change my mind</strong>
                    {verdict.what_would_change_mind.map((c, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', padding: '3px 0', color: 'var(--text-secondary)' }}>• {c}</div>
                    ))}
                </div>
            )}

            <div className="grid grid-2" style={{ gap: 12 }}>
                <div>
                    <strong style={{ fontSize: '0.7rem', color: 'var(--accent-green)', textTransform: 'uppercase' }}>Bull case</strong>
                    {(verdict.bull_case || []).map((c, i) => (
                        <div key={i} style={{ fontSize: '0.78rem', padding: '4px 0' }}>↑ {c.claim} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>[{(c.evidence_refs || []).join(', ')}]</span></div>
                    ))}
                </div>
                <div>
                    <strong style={{ fontSize: '0.7rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>Bear case</strong>
                    {(verdict.bear_case || []).map((c, i) => (
                        <div key={i} style={{ fontSize: '0.78rem', padding: '4px 0' }}>↓ {c.claim} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>[{(c.evidence_refs || []).join(', ')}]</span></div>
                    ))}
                </div>
            </div>

            {verdict.trade_plan && Object.keys(verdict.trade_plan).length > 0 && (
                <div style={{ marginTop: 14, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                    <strong style={{ fontSize: '0.72rem', color: 'var(--accent-blue-bright)', textTransform: 'uppercase' }}>📐 Trade plan</strong>
                    <div style={{ fontSize: '0.78rem', marginTop: 6, lineHeight: 1.7 }}>
                        {verdict.trade_plan.entry_zone && (
                            <div>Entry: <code>${verdict.trade_plan.entry_zone.lower} – ${verdict.trade_plan.entry_zone.upper}</code> <span style={{ color: 'var(--text-muted)' }}>({verdict.trade_plan.entry_zone.logic})</span></div>
                        )}
                        {verdict.trade_plan.stop_price && (
                            <div>Stop: <code>${verdict.trade_plan.stop_price}</code> <span style={{ color: 'var(--text-muted)' }}>({verdict.trade_plan.stop_methodology})</span></div>
                        )}
                        {verdict.trade_plan.targets?.length > 0 && (
                            <div>Targets: {verdict.trade_plan.targets.map(t => `$${t.price} (${t.size_to_take_off_pct}%)`).join(', ')}</div>
                        )}
                        {verdict.trade_plan.time_stop && <div>Time stop: <span style={{ color: 'var(--text-muted)' }}>{verdict.trade_plan.time_stop}</span></div>}
                        <div style={{ marginTop: 6 }}>Size: <strong>{verdict.trade_plan.position_size_pct?.toFixed(1)}%</strong> of portfolio <span style={{ color: 'var(--text-muted)' }}>— {verdict.trade_plan.rationale}</span></div>
                    </div>
                </div>
            )}
        </div>
    );
}


function MemoDeltaCard({ delta }) {
    if (!delta) return null;
    return (
        <div className="glass-card fade-in" style={{ padding: 14, borderColor: 'rgba(124,58,237,0.3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <strong style={{ color: 'var(--accent-purple)' }}>📓 Living Memo updated</strong>
                {delta.new_version && <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>v{delta.new_version}</span>}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{delta.delta_summary}</div>
            {delta.error && <div className="alert alert-warning" style={{ fontSize: '0.75rem', marginTop: 6 }}>{delta.error}</div>}
        </div>
    );
}


export default function DeepResearchV2Page() {
    const [ticker, setTicker] = useState('');
    const [budget, setBudget] = useState('normal');
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState(null);
    const [reportId, setReportId] = useState(null);
    const [sectorInfo, setSectorInfo] = useState(null);
    const [plans, setPlans] = useState([]);          // [{iteration, ...plan}]
    const [toolCalls, setToolCalls] = useState([]); // [tool_call_complete or _error]
    const [debateTurns, setDebateTurns] = useState({}); // { bull: ..., bear: ..., judge: ... }
    const [verdict, setVerdict] = useState(null);
    const [critique, setCritique] = useState(null);
    const [memoDelta, setMemoDelta] = useState(null);
    const [reportComplete, setReportComplete] = useState(null);
    const closeRef = useRef(null);

    const reset = useCallback(() => {
        setError(null); setReportId(null); setSectorInfo(null); setPlans([]);
        setToolCalls([]); setDebateTurns({}); setVerdict(null); setCritique(null);
        setMemoDelta(null); setReportComplete(null);
    }, []);

    const start = useCallback(() => {
        const t = ticker.trim().toUpperCase();
        if (!t) return;
        reset();
        setIsStreaming(true);

        const close = streamDeepResearchV2(t, {
            onPipelineStart: (d) => setReportId(d.report_id),
            onContextLoaded: (d) => setSectorInfo(d),
            onAgentPlan: (d) => setPlans(prev => [...prev, d]),
            onToolCallStart: () => {},
            onToolCallComplete: (d) => setToolCalls(prev => [...prev, d]),
            onToolCallError: (d) => setToolCalls(prev => [...prev, { ...d, error: d.error }]),
            onDebateStart: () => {},
            onDebateTurn: (d) => setDebateTurns(prev => ({ ...prev, [d.agent]: d.output })),
            onDebateComplete: (d) => setVerdict(d.verdict),
            onSelfCritiqueStart: () => {},
            onSelfCritique: (d) => setCritique(d),
            onMemoDeltaProposed: (d) => setMemoDelta(d),
            onBudgetWarning: (d) => console.warn('Budget warning:', d),
            onReportComplete: (d) => { setReportComplete(d); setIsStreaming(false); },
            onError: (d) => { setError(d.error || 'stream error'); setIsStreaming(false); },
        }, { budget });
        closeRef.current = close;
    }, [ticker, budget, reset]);

    const cancel = useCallback(() => {
        closeRef.current?.();
        setIsStreaming(false);
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        start();
    };

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">🧠 Deep Research v2</h1>
                    <p className="page-subtitle">Agentic loop · Bull/Bear/Judge debate · Living Memo · Citation-first</p>
                </div>
                {isStreaming && <button className="btn btn-danger" onClick={cancel}>⏹ Stop</button>}
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, marginBottom: 'var(--spacing-xl)', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                    id="deep-research-v2-input"
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
                <button id="btn-deep-research-v2" className="btn btn-primary" type="submit" disabled={isStreaming || !ticker.trim()}>
                    {isStreaming ? <><span className="spinner spinner-sm" /> Researching…</> : '🚀 Research'}
                </button>
                {reportComplete && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        ✅ {reportComplete.evidence_tool_count} tools · ${reportComplete.cost_used_usd?.toFixed(3)} · {reportComplete.wall_clock_sec}s
                    </span>
                )}
            </form>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-lg)' }}>{error}</div>}

            {/* Sector + context badge */}
            {sectorInfo && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge badge-blue" style={{ fontSize: '0.75rem' }}>Sector: {sectorInfo.sector_key}</span>
                    {sectorInfo.memo_version > 0 && <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>Memo v{sectorInfo.memo_version} loaded</span>}
                    {sectorInfo.open_questions_count > 0 && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{sectorInfo.open_questions_count} open question(s) from prior memo</span>}
                    {sectorInfo.required_tools?.length > 0 && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Required: {sectorInfo.required_tools.join(', ')}</span>
                    )}
                </div>
            )}

            {/* Plans + tool calls — interleaved by appearance order is OK */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                {plans.map((p, i) => <AgentPlanCard key={`plan-${i}`} plan={p} iteration={i} />)}

                {toolCalls.length > 0 && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                        {toolCalls.map((c, i) => <ToolCallCard key={`tc-${i}`} call={c} />)}
                    </div>
                )}

                {debateTurns.bull && <DebateCard agent="bull" output={debateTurns.bull} />}
                {debateTurns.bear && <DebateCard agent="bear" output={debateTurns.bear} />}
                {verdict && <VerdictCard verdict={verdict} />}

                {critique?.weakest_claims?.length > 0 && (
                    <details className="glass-card" style={{ padding: 12 }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 600 }}>🔍 Self-critique: {critique.weakest_claims.length} weak claim(s){critique.should_revise_verdict ? ' — revision suggested' : ''}</summary>
                        <div style={{ marginTop: 10 }}>
                            {critique.weakest_claims.map((c, i) => (
                                <div key={i} style={{ padding: '6px 0', fontSize: '0.78rem', borderBottom: '1px solid var(--border-color)' }}>
                                    <div><strong>{c.claim}</strong></div>
                                    <div style={{ color: 'var(--text-muted)' }}>Why weak: {c.why_weak}</div>
                                    <div style={{ color: 'var(--text-muted)' }}>Would be falsified by: {c.would_be_falsified_by}</div>
                                </div>
                            ))}
                            {critique.revision_suggestion && <div style={{ marginTop: 8, fontSize: '0.78rem' }}><strong>Suggested revision:</strong> {critique.revision_suggestion}</div>}
                        </div>
                    </details>
                )}

                <MemoDeltaCard delta={memoDelta} />

                {reportId && !isStreaming && (
                    <div style={{ textAlign: 'center', padding: 'var(--spacing-md)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Report ID: <code>{reportId}</code>
                    </div>
                )}
            </div>

            {/* Empty state */}
            {!isStreaming && !reportId && (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🧠</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>v2 Living Analyst</h3>
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

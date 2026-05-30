/**
 * StreamView — renders the live SSE activity of a Console run: sector context,
 * planner rounds, tool calls, debate turns, and the final verdict.
 *
 * Phase 1 consumes the existing v2 deep-research event stream. Phase 4 extends
 * this to the full console_orchestrator command set.
 */
export default function StreamView({ run }) {
    if (!run) return null;
    const { sectorInfo, toolCalls, debateTurns, verdict, error, complete } = run;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            {error && <div className="alert alert-error">{error}</div>}

            {sectorInfo && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge badge-blue">Sector: {sectorInfo.sector_key}</span>
                    {sectorInfo.memo_version > 0 && <span className="badge badge-purple">Memo v{sectorInfo.memo_version}</span>}
                </div>
            )}

            {toolCalls.length > 0 && (
                <div className="glass-card" style={{ cursor: 'default' }}>
                    <h4 style={{ fontSize: '0.78rem', margin: '0 0 8px 0', color: 'var(--text-secondary)' }}>
                        Tool calls ({toolCalls.length})
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 6 }}>
                        {toolCalls.map((c, i) => (
                            <div key={i} style={{
                                padding: '6px 10px', fontSize: '0.72rem',
                                borderLeft: `3px solid ${c.error ? 'var(--accent-red)' : 'var(--accent-green)'}`,
                                background: 'rgba(255,255,255,0.02)',
                            }}>
                                <code style={{ color: 'var(--accent-blue-bright)', fontWeight: 600 }}>{c.tool}</code>
                                <span style={{ color: 'var(--text-muted)', float: 'right' }}>{c.latency_ms}ms</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {debateTurns.bull && (
                <div className="glass-card" style={{ cursor: 'default', borderLeft: '3px solid var(--accent-green)' }}>
                    <strong style={{ color: 'var(--accent-green)', fontSize: '0.78rem' }}>Bull</strong>
                    <div style={{ fontSize: '0.78rem', marginTop: 4, whiteSpace: 'pre-line', color: 'var(--text-secondary)' }}>
                        {debateTurns.bull.thesis_md?.slice(0, 600)}
                    </div>
                </div>
            )}
            {debateTurns.bear && (
                <div className="glass-card" style={{ cursor: 'default', borderLeft: '3px solid var(--accent-red)' }}>
                    <strong style={{ color: 'var(--accent-red)', fontSize: '0.78rem' }}>Bear</strong>
                    <div style={{ fontSize: '0.78rem', marginTop: 4, whiteSpace: 'pre-line', color: 'var(--text-secondary)' }}>
                        {(debateTurns.bear.attack_md || debateTurns.bear.independent_bear_md)?.slice(0, 600)}
                    </div>
                </div>
            )}

            {verdict && (
                <div className="glass-card" style={{ cursor: 'default' }}>
                    <h4 style={{ fontSize: '0.85rem', margin: '0 0 6px 0' }}>Judge Verdict</h4>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                        {verdict.recommendation && <span className="badge badge-blue">{verdict.recommendation}</span>}
                        {verdict.conviction && <span className="badge badge-purple">{verdict.conviction} conviction</span>}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line' }}>
                        {verdict.summary}
                    </div>
                </div>
            )}

            {complete && (
                <div className="alert alert-success" style={{ fontSize: '0.76rem' }}>
                    Run complete · {complete.evidence_tool_count} tools · ${Number(complete.cost_used_usd || 0).toFixed(3)} · {complete.wall_clock_sec}s
                </div>
            )}
        </div>
    );
}

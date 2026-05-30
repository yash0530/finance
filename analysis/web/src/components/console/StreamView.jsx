/**
 * StreamView — renders the live SSE activity of a Console run across all
 * command types: deep research (tool calls, debate, verdict), /why quick takes,
 * /theme verdicts, and /compare rankings.
 */
function ToolCalls({ toolCalls }) {
    if (!toolCalls.length) return null;
    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <h4 style={{ fontSize: '0.78rem', margin: '0 0 8px 0', color: 'var(--text-secondary)' }}>
                Tool calls ({toolCalls.length})
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 6 }}>
                {toolCalls.map((c, i) => (
                    <div key={i} style={{
                        padding: '6px 10px', fontSize: '0.72rem',
                        borderLeft: `3px solid ${c.error ? 'var(--accent-red)' : 'var(--accent-green)'}`,
                        background: 'rgba(255,255,255,0.02)',
                    }}>
                        <code style={{ color: 'var(--accent-blue-bright)', fontWeight: 600 }}>{c.tool}</code>
                        {c.args?.ticker && <span style={{ color: 'var(--text-muted)' }}> {c.args.ticker}</span>}
                        <span style={{ color: 'var(--text-muted)', float: 'right' }}>{c.latency_ms}ms</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function Verdict({ verdict, title = 'Judge Verdict' }) {
    if (!verdict) return null;
    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <h4 style={{ fontSize: '0.85rem', margin: '0 0 6px 0' }}>{title}</h4>
            <div style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                {verdict.recommendation && <span className="badge badge-blue">{verdict.recommendation}</span>}
                {verdict.conviction && <span className="badge badge-purple">{verdict.conviction} conviction</span>}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line' }}>
                {verdict.summary}
            </div>
        </div>
    );
}

export default function StreamView({ run }) {
    if (!run) return null;
    const { sectorInfo, toolCalls, debateTurns, verdict, quickTake, compare, themeInfo, error, complete } = run;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            {error && <div className="alert alert-error">{error}</div>}

            {quickTake && (
                <div className="glass-card" style={{ cursor: 'default', borderLeft: '3px solid var(--accent-blue)' }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <strong style={{ fontSize: '0.82rem' }}>{quickTake.ticker} · quick take</strong>
                        {quickTake.stance && <span className="badge badge-blue" style={{ fontSize: '0.62rem' }}>{quickTake.stance}</span>}
                        {quickTake.cached && <span className="badge badge-gray" style={{ fontSize: '0.62rem' }}>cached</span>}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{quickTake.why_md}</div>
                    {quickTake.evidence_refs?.length > 0 && (
                        <div style={{ fontSize: '0.64rem', color: 'var(--text-muted)', marginTop: 4 }}>{quickTake.evidence_refs.join(', ')}</div>
                    )}
                </div>
            )}

            {themeInfo && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge badge-purple">Theme: {themeInfo.name}</span>
                    <span className="badge badge-gray">{themeInfo.ticker_count} constituents</span>
                </div>
            )}

            {sectorInfo && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge badge-blue">Sector: {sectorInfo.sector_key}</span>
                    {sectorInfo.memo_version > 0 && <span className="badge badge-purple">Memo v{sectorInfo.memo_version}</span>}
                </div>
            )}

            <ToolCalls toolCalls={toolCalls} />

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

            <Verdict verdict={verdict} title={themeInfo ? 'Theme Verdict' : 'Judge Verdict'} />

            {compare?.candidates?.length > 0 && (
                <div className="glass-card" style={{ cursor: 'default' }}>
                    <h4 style={{ fontSize: '0.82rem', margin: '0 0 8px 0' }}>Candidates</h4>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {compare.candidates.map(c => (
                            <span key={c.ticker} className="badge badge-gray" style={{ fontSize: '0.68rem' }}>
                                {c.ticker} · {c.recommendation || '—'} {c.conviction ? `(${c.conviction})` : ''}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {compare?.ranking && (
                <div className="glass-card" style={{ cursor: 'default' }}>
                    <h4 style={{ fontSize: '0.85rem', margin: '0 0 6px 0' }}>
                        Ranking{compare.ranking.winner ? ` · winner ${compare.ranking.winner}` : ''}
                    </h4>
                    <ol style={{ margin: '0 0 8px 18px', padding: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {(compare.ranking.ranking || []).map(r => (
                            <li key={r.ticker} style={{ marginBottom: 3 }}>
                                <strong style={{ color: 'var(--text-primary)' }}>{r.ticker}</strong> — {r.reason}
                            </li>
                        ))}
                    </ol>
                    {compare.ranking.head_to_head && (
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{compare.ranking.head_to_head}</div>
                    )}
                </div>
            )}

            {complete && (
                <div className="alert alert-success" style={{ fontSize: '0.76rem' }}>
                    Run complete
                    {complete.evidence_tool_count != null ? ` · ${complete.evidence_tool_count} tools` : ''}
                    {complete.cost_used_usd != null ? ` · $${Number(complete.cost_used_usd).toFixed(3)}` : ''}
                    {complete.wall_clock_sec != null ? ` · ${complete.wall_clock_sec}s` : ''}
                </div>
            )}
        </div>
    );
}

import React, { useState } from 'react';

/**
 * Collapsible per-tool evidence ledger.
 */
export default function EvidenceLedger({ results = [] }) {
    if (!results.length) return null;

    return (
        <div className="glass-card fade-in">
            <h3 style={{ fontSize: '0.85rem', margin: '0 0 var(--spacing-md) 0', color: 'var(--text-primary)' }}>
                 📋 Evidence Ledger ({results.length} tool{results.length === 1 ? '' : 's'})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {results.map((r, i) => (
                    <EvidenceRow key={i} result={r} />
                ))}
            </div>
        </div>
    );
}

function EvidenceRow({ result }) {
    const [open, setOpen] = useState(false);
    const ok = !result.error;
    const sources = result.sources || [];

    return (
        <div style={{
            padding: '8px 12px',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-sm)',
            borderLeft: `3px solid ${ok ? 'var(--accent-green)' : 'var(--accent-red)'}`,
        }}>
            <div
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => setOpen(!open)}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <code style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-blue-bright)' }}>
                        {result.tool_name || result.tool}
                    </code>
                    <span className={`badge badge-${result.confidence === 'high' ? 'green' : result.confidence === 'medium' ? 'yellow' : 'gray'}`}
                          style={{ fontSize: '0.6rem' }}>
                        {result.confidence}
                    </span>
                    {result.cached && <span className="badge badge-blue" style={{ fontSize: '0.6rem' }}>cached</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {result.latency_ms != null && (
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                            {result.latency_ms}ms
                        </span>
                    )}
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{open ? '▾' : '▸'}</span>
                </div>
            </div>

            {open && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-color)' }}>
                    {result.error ? (
                        <div className="alert alert-warning" style={{ fontSize: '0.75rem' }}>{result.error}</div>
                    ) : (
                        <>
                            {result.data && (
                                <pre style={{ fontSize: '0.68rem', maxHeight: 200, overflow: 'auto', background: 'var(--bg-primary)', padding: 8, borderRadius: 4 }}>
                                    {JSON.stringify(result.data, null, 2)}
                                </pre>
                            )}
                            {sources.length > 0 && (
                                <div style={{ marginTop: 6, fontSize: '0.7rem' }}>
                                    {sources.slice(0, 5).map((s, i) => (
                                        <div key={i} style={{ color: 'var(--text-muted)', padding: '2px 0' }}>
                                            📎 {s.tool || ''}:{s.field || ''}{s.url ? ` — ${s.url}` : ''}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

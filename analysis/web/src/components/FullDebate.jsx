import React from 'react';

/**
 * Collapsible 3-section debate: Bull, Bear, Judge reasoning.
 */
export default function FullDebate({ bull, bear, verdict }) {
    if (!bull && !bear) return null;

    return (
        <details className="glass-card fade-in" style={{ padding: 'var(--spacing-md)' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', outline: 'none' }}>
                 Full Debate (Bull / Bear / Judge)
            </summary>
            <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                {/* Bull */}
                {bull && (
                    <div style={{ padding: 14, borderLeft: '3px solid var(--accent-green)', background: 'rgba(16, 217, 160, 0.04)', borderRadius: 'var(--radius-sm)' }}>
                        <strong style={{ fontSize: '0.8rem', color: 'var(--accent-green)', textTransform: 'uppercase' }}> Bull</strong>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 8, whiteSpace: 'pre-line' }}>
                            {bull.thesis_md || ''}
                        </div>
                        {bull.key_drivers?.length > 0 && (
                            <div style={{ marginTop: 10 }}>
                                {bull.key_drivers.map((d, i) => (
                                    <div key={i} style={{ fontSize: '0.75rem', padding: '3px 0' }}>
                                         {d.claim} <span style={{ color: 'var(--text-muted)' }}>[{(d.evidence_refs || []).join(', ')}]</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Bear */}
                {bear && (
                    <div style={{ padding: 14, borderLeft: '3px solid var(--accent-red)', background: 'rgba(244, 63, 94, 0.04)', borderRadius: 'var(--radius-sm)' }}>
                        <strong style={{ fontSize: '0.8rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}> Bear</strong>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 8, whiteSpace: 'pre-line' }}>
                            {bear.attack_md || ''}
                        </div>
                        {bear.independent_bear_md && (
                            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border-color)', fontSize: '0.8rem', whiteSpace: 'pre-line' }}>
                                <strong style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Independent bear case</strong>
                                <div style={{ marginTop: 6 }}>{bear.independent_bear_md}</div>
                            </div>
                        )}
                        {bear.key_risks?.length > 0 && (
                            <div style={{ marginTop: 10 }}>
                                {bear.key_risks.map((r, i) => (
                                    <div key={i} style={{ fontSize: '0.75rem', padding: '3px 0' }}>
                                         ⚠ {r.risk} <span className={`badge badge-${r.severity === 'high' ? 'red' : 'yellow'}`} style={{ fontSize: '0.6rem', marginLeft: 4 }}>{r.severity}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Judge reasoning */}
                {verdict && (
                    <div style={{ padding: 14, borderLeft: '3px solid var(--accent-blue)', background: 'rgba(45, 126, 247, 0.04)', borderRadius: 'var(--radius-sm)' }}>
                        <strong style={{ fontSize: '0.8rem', color: 'var(--accent-blue)', textTransform: 'uppercase' }}>⚖️ Judge Reasoning</strong>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginTop: 8 }}>
                            {verdict.summary}
                        </div>
                    </div>
                )}
            </div>
        </details>
    );
}

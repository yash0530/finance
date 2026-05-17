import React from 'react';

/**
 * 2-column synthesized bull/bear case with evidence chips.
 */
export default function ThesisGlance({ bullCase = [], bearCase = [] }) {
    if (!bullCase.length && !bearCase.length) return null;

    return (
        <div className="glass-card fade-in">
            <h3 style={{ fontSize: '0.85rem', margin: '0 0 var(--spacing-md) 0', color: 'var(--text-primary)' }}>
                Thesis at a Glance
            </h3>
            <div className="grid grid-2" style={{ gap: 'var(--spacing-lg)' }}>
                <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-green)', marginBottom: 8 }}>
                        ↑ Synthesized Bull Case
                    </div>
                    {bullCase.map((item, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8, lineHeight: 1.5 }}>
                            <span style={{ color: 'var(--accent-green)', flexShrink: 0 }}>↑</span>
                            <span>
                                {item.claim || item}
                                {item.evidence_refs?.length > 0 && (
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginLeft: 6 }}>
                                        [{item.evidence_refs.join(', ')}]
                                    </span>
                                )}
                            </span>
                        </div>
                    ))}
                </div>
                <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-red)', marginBottom: 8 }}>
                        ↓ Synthesized Bear Case
                    </div>
                    {bearCase.map((item, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8, lineHeight: 1.5 }}>
                            <span style={{ color: 'var(--accent-red)', flexShrink: 0 }}>↓</span>
                            <span>
                                {item.claim || item}
                                {item.evidence_refs?.length > 0 && (
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginLeft: 6 }}>
                                        [{item.evidence_refs.join(', ')}]
                                    </span>
                                )}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

import React from 'react';

/**
 * Living Memo delta panel — shows new version + delta summary.
 */
export default function MemoDeltaPanel({ delta }) {
    if (!delta) return null;

    return (
        <details className="glass-card fade-in" style={{ padding: 'var(--spacing-md)', borderColor: 'rgba(124, 58, 237, 0.3)' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', outline: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📓 Living Memo Update</span>
                {delta.new_version && <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>v{delta.new_version}</span>}
            </summary>
            <div style={{ marginTop: 'var(--spacing-md)' }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {delta.delta_summary || 'No summary available'}
                </div>
                {delta.error && (
                    <div className="alert alert-warning" style={{ fontSize: '0.75rem', marginTop: 8 }}>{delta.error}</div>
                )}
                {delta.new_memo && (
                    <details style={{ marginTop: 10 }}>
                        <summary style={{ fontSize: '0.72rem', color: 'var(--text-muted)', cursor: 'pointer' }}>View memo content</summary>
                        <pre style={{ fontSize: '0.68rem', maxHeight: 300, overflow: 'auto', background: 'var(--bg-secondary)', padding: 8, borderRadius: 4, marginTop: 6 }}>
                            {JSON.stringify(delta.new_memo, null, 2)}
                        </pre>
                    </details>
                )}
            </div>
        </details>
    );
}

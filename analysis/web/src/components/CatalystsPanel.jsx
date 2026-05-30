import React from 'react';

/**
 * Purple panel with catalyst events and date pills.
 */
export default function CatalystsPanel({ items = [] }) {
    if (!items.length) return null;

    return (
        <div className="glass-card fade-in" style={{
            background: 'rgba(124, 58, 237, 0.06)',
            borderColor: 'rgba(124, 58, 237, 0.25)',
            border: '1px solid rgba(124, 58, 237, 0.2)',
        }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-purple)', marginBottom: 10 }}>
                Key Catalysts
            </div>
            {items.map((cat, i) => {
                const event = typeof cat === 'string' ? cat : cat.event;
                const date = typeof cat === 'string' ? null : cat.date;
                const impact = typeof cat === 'string' ? null : cat.expected_impact;
                return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0' }}>
                        <span style={{ color: 'var(--accent-purple)', fontSize: '0.68rem', fontWeight: 700 }}>CAT</span>
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', flex: 1 }}>{event}</span>
                        {date && (
                            <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>{date}</span>
                        )}
                        {impact && (
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{impact}</span>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

import React from 'react';

/**
 * Yellow warning panel: "What would change my mind" conditions.
 */
export default function ChangeMyMindPanel({ items = [] }) {
    if (!items.length) return null;

    return (
        <div className="glass-card fade-in" style={{
            background: 'rgba(245, 158, 11, 0.06)',
            borderColor: 'rgba(245, 158, 11, 0.25)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
        }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-yellow)', marginBottom: 10 }}>
                What Would Change My Mind
            </div>
            {items.map((item, i) => (
                <div key={i} style={{ fontSize: '0.82rem', padding: '5px 0', color: 'var(--text-secondary)', display: 'flex', gap: 8, lineHeight: 1.5 }}>
                    <span style={{ color: 'var(--accent-yellow)', flexShrink: 0 }}>Risk</span>
                    <span>{item}</span>
                </div>
            ))}
        </div>
    );
}

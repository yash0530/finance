import React from 'react';

/**
 * Vertical target ladder with colored dots and prices.
 * Mirrors the RiskCard pattern from v1.
 */
export default function TargetLadder({ targets = [], entry, stop, currentPrice }) {
    if (!targets.length && !entry && !stop) return null;

    const allLevels = [];

    // Targets (green, top)
    targets.forEach((t, i) => {
        allLevels.push({
            price: t.price,
            label: `T${i + 1}`,
            detail: `${t.size_to_take_off_pct}% — ${t.rationale || ''}`,
            color: 'var(--accent-green)',
            type: 'target',
        });
    });

    // Entry zone (blue)
    if (entry) {
        allLevels.push({
            price: (entry.lower + entry.upper) / 2,
            label: 'Entry',
            detail: `$${entry.lower} – $${entry.upper}`,
            color: 'var(--accent-blue-bright)',
            type: 'entry',
        });
    }

    // Stop (red, bottom)
    if (stop) {
        allLevels.push({
            price: stop,
            label: 'Stop',
            detail: `$${stop}`,
            color: 'var(--accent-red)',
            type: 'stop',
        });
    }

    // Sort descending by price
    allLevels.sort((a, b) => b.price - a.price);

    return (
        <div style={{ position: 'relative', paddingLeft: 20, borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {allLevels.map((level, i) => (
                <div key={i} style={{ position: 'relative' }}>
                    <div style={{
                        position: 'absolute', left: -25, top: 4,
                        width: 8, height: 8, borderRadius: '50%',
                        background: level.color,
                    }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', color: level.color, fontWeight: 600 }}>
                            {level.label}
                        </span>
                        {level.type === 'target' && (
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                {level.detail}
                            </span>
                        )}
                    </div>
                    <div style={{ fontSize: '1rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)', fontWeight: 600 }}>
                        {level.type === 'entry' ? level.detail : `$${level.price}`}
                    </div>
                    {currentPrice && level.price && (
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            {level.price > currentPrice
                                ? `+${(((level.price - currentPrice) / currentPrice) * 100).toFixed(1)}%`
                                : `${(((level.price - currentPrice) / currentPrice) * 100).toFixed(1)}%`
                            }
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
}

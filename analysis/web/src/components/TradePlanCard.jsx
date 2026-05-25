import React from 'react';
import TargetLadder from './TargetLadder';

/**
 * Trade plan card: entry/stop/target ladder + sizing.
 */
export default function TradePlanCard({ plan, currentPrice }) {
    if (!plan || !Object.keys(plan).length) return null;

    return (
        <div className="glass-card fade-in" style={{ borderColor: 'rgba(45, 126, 247, 0.3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
                <h3 style={{ fontSize: '0.9rem', margin: 0, color: 'var(--text-primary)' }}>Trade Plan</h3>
                {plan.position_size_pct != null && (
                    <span className="badge badge-blue" style={{ fontSize: '0.75rem' }}>
                        {plan.position_size_pct.toFixed(1)}% of portfolio
                    </span>
                )}
            </div>

            <div className="grid grid-2" style={{ gap: 'var(--spacing-lg)' }}>
                {/* Left: Target Ladder */}
                <div>
                    <TargetLadder
                        targets={plan.targets || []}
                        entry={plan.entry_zone}
                        stop={plan.stop_price}
                        currentPrice={currentPrice}
                    />
                </div>

                {/* Right: Details */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {plan.entry_zone && (
                        <div style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Entry Zone</div>
                            <div style={{ fontSize: '0.85rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-blue-bright)' }}>
                                ${plan.entry_zone.lower} – ${plan.entry_zone.upper}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>{plan.entry_zone.logic}</div>
                        </div>
                    )}

                    {plan.stop_price && (
                        <div style={{ padding: '10px 12px', background: 'rgba(244, 63, 94, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(244, 63, 94, 0.2)' }}>
                            <div style={{ fontSize: '0.65rem', color: 'var(--accent-red)', textTransform: 'uppercase' }}>Stop Loss</div>
                            <div style={{ fontSize: '0.85rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-red)' }}>
                                ${plan.stop_price}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>{plan.stop_methodology}</div>
                        </div>
                    )}

                    {plan.time_stop && (
                        <div style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', fontSize: '0.78rem' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Time stop: </span>
                            <span style={{ color: 'var(--text-secondary)' }}>{plan.time_stop}</span>
                        </div>
                    )}

                    {plan.rationale && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.6, marginTop: 4 }}>
                            {plan.rationale}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

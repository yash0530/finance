import React from 'react';

export default function RiskCard({ riskData }) {
    if (!riskData || riskData.error) return null;

    const { recommended_weight_pct, position_size_usd, shares_to_buy, risk_metrics } = riskData;
    
    // Safety check in case metrics are missing
    if (!risk_metrics) return null;

    return (
        <div className="glass-card fade-in" style={{ borderColor: 'rgba(239, 68, 68, 0.25)' }}>
            <div className="card-header" style={{ marginBottom: 'var(--spacing-md)' }}>
                <span className="card-title">Risk & Position Sizing</span>
                <span className="badge badge-purple">Half-Kelly Criterion</span>
            </div>

            <div className="grid grid-2" style={{ gap: 'var(--spacing-lg)' }}>
                {/* Left Column: Sizing Recommendation */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                    <div style={{ background: 'var(--bg-secondary)', padding: 'var(--spacing-md)', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Recommended Size
                        </div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 4 }}>
                            <span style={{ fontSize: '1.8rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--accent-blue-bright)' }}>
                                {recommended_weight_pct}%
                            </span>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>of capital</span>
                        </div>
                        
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
                            <div>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Capital Allocation</div>
                                <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                                    ${position_size_usd.toLocaleString()}
                                </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Target Shares</div>
                                <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                                    {shares_to_buy}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>Dollars at Risk (1R)</span>
                        <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', fontWeight: 600, color: 'var(--accent-red)' }}>
                            ${risk_metrics.dollars_at_risk.toLocaleString()}
                        </span>
                    </div>
                </div>

                {/* Right Column: Trade Plan */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)' }}>
                        <div>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Win Probability</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>{risk_metrics.win_probability_est_pct}%</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reward / Risk</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>{risk_metrics.reward_risk_ratio}x</div>
                        </div>
                    </div>

                    <div style={{ position: 'relative', marginTop: 12, paddingLeft: 20, borderLeft: '2px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: 16 }}>
                        
                        {/* Take Profit */}
                        <div style={{ position: 'relative' }}>
                            <div style={{ position: 'absolute', left: -25, top: 4, width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-green)' }} />
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--accent-green)', fontWeight: 600 }}>Take Profit</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--accent-green)' }}>+{risk_metrics.take_profit_pct}%</span>
                            </div>
                            <div style={{ fontSize: '1.1rem', fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>
                                ${risk_metrics.take_profit_price.toFixed(2)}
                            </div>
                        </div>

                        {/* Stop Loss */}
                        <div style={{ position: 'relative' }}>
                            <div style={{ position: 'absolute', left: -25, top: 4, width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-red)' }} />
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--accent-red)', fontWeight: 600 }}>Stop Loss</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>-{risk_metrics.stop_loss_pct}%</span>
                            </div>
                            <div style={{ fontSize: '1.1rem', fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>
                                ${risk_metrics.stop_loss_price.toFixed(2)}
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
}

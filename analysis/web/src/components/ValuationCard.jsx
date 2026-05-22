import React from 'react';

export default function ValuationCard({ valuation }) {
    if (!valuation || valuation.error || valuation.skipped) return null;

    const { intrinsic_value, peer_valuation } = valuation;

    if (!intrinsic_value || intrinsic_value.error) {
        return (
             <div className="glass-card fade-in">
                <div className="card-header"><span className="card-title"> Valuation & Intrinsic Value</span></div>
                <div className="alert alert-warning" style={{ fontSize: '0.8rem' }}>
                    {intrinsic_value?.error || 'Valuation data unavailable for this ticker'}
                </div>
            </div>
        );
    }

    const { base_case, bull_case, bear_case, current_price, margin_of_safety_pct, verdict, implied_growth_rate } = intrinsic_value;

    const isUndervalued = current_price < base_case;
    const isDeeplyUndervalued = current_price < bear_case;
    const isFairlyValued = current_price >= base_case && current_price < bull_case;

    const mosClass = isDeeplyUndervalued ? 'badge-green' : isUndervalued ? 'badge-blue' : isFairlyValued ? 'badge-yellow' : 'badge-red';
    
    // Calculate slider position (min 0, max 100)
    const minVal = Math.min(bear_case, current_price) * 0.9;
    const maxVal = Math.max(bull_case, current_price) * 1.1;
    const range = maxVal - minVal;
    
    const getPos = (val) => Math.max(0, Math.min(100, ((val - minVal) / range) * 100));
    const currentPos = getPos(current_price);
    const bearPos = getPos(bear_case);
    const basePos = getPos(base_case);
    const bullPos = getPos(bull_case);

    return (
        <div className="glass-card fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            <div className="card-header" style={{ marginBottom: 0 }}>
                <span className="card-title"> DCF Valuation (5-Year)</span>
                <span className={`badge ${mosClass}`}>{verdict}</span>
            </div>

            {/* DCF Scenarios */}
            <div style={{ background: 'var(--bg-secondary)', padding: 'var(--spacing-md)', borderRadius: 'var(--radius-md)' }}>
                 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
                     <div style={{ textAlign: 'center' }}>
                         <div style={{ fontSize: '0.7rem', color: 'var(--accent-red)', textTransform: 'uppercase', fontWeight: 600 }}>Bear Case</div>
                         <div style={{ fontFamily: 'monospace', fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>${bear_case.toFixed(2)}</div>
                         <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Low growth</div>
                     </div>
                     <div style={{ textAlign: 'center' }}>
                         <div style={{ fontSize: '0.7rem', color: 'var(--accent-blue)', textTransform: 'uppercase', fontWeight: 600 }}>Base Case</div>
                         <div style={{ fontFamily: 'monospace', fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-blue-bright)' }}>${base_case.toFixed(2)}</div>
                         <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{implied_growth_rate}% implied growth</div>
                     </div>
                     <div style={{ textAlign: 'center' }}>
                         <div style={{ fontSize: '0.7rem', color: 'var(--accent-green)', textTransform: 'uppercase', fontWeight: 600 }}>Bull Case</div>
                         <div style={{ fontFamily: 'monospace', fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>${bull_case.toFixed(2)}</div>
                         <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>High growth</div>
                     </div>
                 </div>

                 {/* Visual Bar */}
                 <div style={{ position: 'relative', height: 40, marginTop: 10 }}>
                     {/* Track */}
                     <div style={{ position: 'absolute', top: 18, left: 0, right: 0, height: 4, background: 'var(--bg-tertiary)', borderRadius: 2 }} />
                     
                     {/* Ranges */}
                     <div style={{ position: 'absolute', top: 18, left: `${bearPos}%`, width: `${basePos - bearPos}%`, height: 4, background: 'rgba(239, 68, 68, 0.4)' }} />
                     <div style={{ position: 'absolute', top: 18, left: `${basePos}%`, width: `${bullPos - basePos}%`, height: 4, background: 'rgba(16, 185, 129, 0.4)' }} />

                     {/* Current Price Marker */}
                     <div style={{ 
                         position: 'absolute', 
                         top: 4, 
                         left: `calc(${currentPos}% - 1px)`, 
                         width: 2, 
                         height: 32, 
                         background: 'var(--text-primary)',
                         zIndex: 10
                     }} />
                     <div style={{
                         position: 'absolute',
                         top: -12,
                         left: `calc(${currentPos}% - 20px)`,
                         width: 40,
                         textAlign: 'center',
                         fontSize: '0.7rem',
                         fontFamily: 'monospace',
                         fontWeight: 700,
                         color: 'var(--text-primary)',
                         background: 'var(--bg-card)',
                         borderRadius: 4,
                         padding: '2px 0',
                         border: '1px solid var(--border-color)',
                         zIndex: 11
                     }}>
                        ${current_price.toFixed(2)}
                     </div>

                     {/* Scenario Markers */}
                     {[
                         { pos: bearPos, label: 'Bear', color: 'var(--accent-red)' },
                         { pos: basePos, label: 'Base', color: 'var(--accent-blue)' },
                         { pos: bullPos, label: 'Bull', color: 'var(--accent-green)' },
                     ].map((m, i) => (
                         <div key={i} style={{ position: 'absolute', top: 14, left: `calc(${m.pos}% - 4px)`, width: 8, height: 12, background: m.color, borderRadius: 4 }} title={m.label} />
                     ))}
                 </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {/* Margin of Safety */}
                <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                     <div>
                         <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Margin of Safety</div>
                         <div style={{ fontSize: '1.1rem', fontWeight: 600, color: margin_of_safety_pct > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                             {margin_of_safety_pct > 0 ? '+' : ''}{margin_of_safety_pct}%
                         </div>
                     </div>
                     <div style={{ fontSize: '1.5rem' }}>{margin_of_safety_pct > 20 ? '' : margin_of_safety_pct > 0 ? '' : ''}</div>
                </div>

                {/* Peer Comparison (mocked) */}
                {peer_valuation && (
                    <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 6 }}>{peer_valuation.sector} Averages</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span>P/E: <span style={{ fontFamily: 'monospace' }}>{peer_valuation.average_pe.toFixed(1)}x</span></span>
                            <span>P/S: <span style={{ fontFamily: 'monospace' }}>{peer_valuation.average_ps.toFixed(1)}x</span></span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

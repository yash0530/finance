import { useState, useEffect } from 'react';
import { getStockTechnicals, formatPercent, formatNumber } from '../../utils/api';
import SectionCard from './SectionCard';
import StockPatternDetails from './StockPatternDetails';

function Badge({ type, children }) {
    const styles = {
        bullish: { bg: 'rgba(15,157,88,0.1)', color: 'var(--accent-green)', border: '1px solid rgba(15,157,88,0.2)' },
        bearish: { bg: 'rgba(219,68,55,0.1)', color: 'var(--accent-red)', border: '1px solid rgba(219,68,55,0.2)' },
        neutral: { bg: 'rgba(255,255,255,0.03)', color: 'var(--text-muted)', border: '1px solid var(--border-color)' }
    };
    const s = styles[type] || styles.neutral;
    return (
        <span style={{
            fontSize: '0.62rem', fontWeight: 600, padding: '2px 6px', borderRadius: 4,
            textTransform: 'uppercase', letterSpacing: '0.04em', background: s.bg, color: s.color, border: s.border
        }}>
            {children}
        </span>
    );
}

export default function StockTechnicals({ ticker }) {
    const [tech, setTech] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const id = window.setTimeout(() => {
            setLoading(true);
            setError(null);

            getStockTechnicals(ticker)
                .then(res => {
                    if (cancelled) return;
                    setTech(res.data || {});
                })
                .catch(e => {
                    if (!cancelled) setError(e.message);
                })
                .finally(() => {
                    if (!cancelled) setLoading(false);
                });
        }, 0);
            
        return () => {
            cancelled = true;
            window.clearTimeout(id);
        };
    }, [ticker]);

    if (loading) return <SectionCard title="Technical Analysis"><div className="loading-state" style={{ minHeight: 120 }}><div className="spinner spinner-sm" /></div></SectionCard>;
    if (error) return <SectionCard title="Technical Analysis"><div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div></SectionCard>;
    if (!tech || tech.error) return <SectionCard title="Technical Analysis"><div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{tech?.error || 'Unavailable'}</div></SectionCard>;

    const rsi = tech.rsi;
    const macd = tech.macd || {};
    const bb = tech.bollinger || {};
    const patterns = tech.patterns || [];
    const spyRs = tech.relative_strength_vs_spy;
    const yearReturnPct = tech.year_return_pct;
    const volatilityPct = tech.annualized_volatility_pct;

    let rsiType = 'neutral';
    if (rsi > 70) rsiType = 'bearish'; // overbought -> bearish warning
    if (rsi < 30) rsiType = 'bullish'; // oversold -> bullish setup

    const macdSignalType = macd.signal_label?.toLowerCase().includes('bull') ? 'bullish' :
                           macd.signal_label?.toLowerCase().includes('bear') ? 'bearish' : 'neutral';

    return (
        <SectionCard title="Technical Analysis" id="section-technicals">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--spacing-lg)' }}>
                {/* RSI Section */}
                <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <span style={{ fontSize: '0.74rem', fontWeight: 600 }}>RSI (14)</span>
                        <Badge type={rsiType}>{rsi != null ? `${rsi.toFixed(1)}` : 'N/A'}</Badge>
                    </div>
                    {rsi != null ? (
                        <div>
                            {/* Visual slider */}
                            <div style={{ position: 'relative', height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, margin: '14px 0 8px 0' }}>
                                {/* oversold boundary */}
                                <div style={{ position: 'absolute', left: '0%', width: '30%', height: '100%', borderRight: '1px dashed rgba(15,157,88,0.4)', background: 'rgba(15,157,88,0.05)' }} />
                                {/* overbought boundary */}
                                <div style={{ position: 'absolute', left: '70%', width: '30%', height: '100%', borderLeft: '1px dashed rgba(219,68,55,0.4)', background: 'rgba(219,68,55,0.05)' }} />
                                {/* Current value indicator pointer */}
                                <div style={{
                                    position: 'absolute', left: `${Math.min(100, Math.max(0, rsi))}%`, top: -3, width: 12, height: 12, borderRadius: '50%',
                                    background: rsiType === 'bullish' ? 'var(--accent-green)' : rsiType === 'bearish' ? 'var(--accent-red)' : 'var(--accent-blue-bright)',
                                    transform: 'translateX(-50%)', border: '2px solid var(--bg-card)', boxShadow: '0 1px 3px rgba(0,0,0,0.5)'
                                }} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', color: 'var(--text-muted)' }}>
                                <span>Oversold (30)</span>
                                <span>Neutral</span>
                                <span>Overbought (70)</span>
                            </div>
                        </div>
                    ) : (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>RSI data unavailable</div>
                    )}
                </div>

                {/* MACD Section */}
                <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <span style={{ fontSize: '0.74rem', fontWeight: 600 }}>MACD (12, 26, 9)</span>
                        <Badge type={macdSignalType}>{macd.signal_label?.replace('_', ' ') || 'N/A'}</Badge>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.72rem', marginTop: 10 }}>
                        <div>
                            <span style={{ color: 'var(--text-muted)' }}>MACD Line: </span>
                            <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600 }}>{formatNumber(macd.macd)}</span>
                        </div>
                        <div>
                            <span style={{ color: 'var(--text-muted)' }}>Signal Line: </span>
                            <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600 }}>{formatNumber(macd.signal)}</span>
                        </div>
                        <div>
                            <span style={{ color: 'var(--text-muted)' }}>Histogram: </span>
                            <span style={{
                                fontFamily: 'var(--font-mono, monospace)', fontWeight: 600,
                                color: (macd.histogram ?? 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                            }}>
                                {formatNumber(macd.histogram)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Bollinger Bands Section */}
                <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <span style={{ fontSize: '0.74rem', fontWeight: 600 }}>Bollinger Bands (20, 2σ)</span>
                        {bb.position != null && (
                            <Badge type={bb.position > 0.8 ? 'bearish' : bb.position < 0.2 ? 'bullish' : 'neutral'}>
                                Pos: {(bb.position * 100).toFixed(0)}%
                            </Badge>
                        )}
                    </div>
                    <div style={{ fontSize: '0.7rem', display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Upper Band</span>
                            <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 500 }}>{bb.upper != null ? `$${formatNumber(bb.upper)}` : '—'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Basis (20 SMA)</span>
                            <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 500 }}>{bb.middle != null ? `$${formatNumber(bb.middle)}` : '—'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Lower Band</span>
                            <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 500 }}>{bb.lower != null ? `$${formatNumber(bb.lower)}` : '—'}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Performance + Extra Technical info */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-md)' }}>
                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>50 / 200 Cross</span>
                    <span style={{ fontSize: '0.76rem', fontWeight: 600 }}>
                        {tech.golden_cross === true ? <span style={{ color: 'var(--accent-green)' }}>Golden Cross</span> :
                         tech.golden_cross === false ? <span style={{ color: 'var(--accent-red)' }}>Death Cross</span> : 'N/A'}
                    </span>
                </div>

                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>1Y Return</span>
                    <span style={{
                        fontSize: '0.76rem', fontWeight: 600,
                        color: (yearReturnPct ?? 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                    }}>
                        {yearReturnPct != null ? formatPercent(yearReturnPct, true) : '—'}
                    </span>
                </div>

                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Annual Volatility</span>
                    <span style={{ fontSize: '0.76rem', fontWeight: 600, fontFamily: 'var(--font-mono, monospace)' }}>
                        {volatilityPct != null ? formatPercent(volatilityPct, true) : '—'}
                    </span>
                </div>

                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Rel. Strength vs SPY</span>
                    <span style={{
                        fontSize: '0.76rem', fontWeight: 600, fontFamily: 'var(--font-mono, monospace)',
                        color: (spyRs ?? 1) >= 1.0 ? 'var(--accent-green)' : 'var(--accent-red)'
                    }}>
                        {spyRs != null ? `${spyRs.toFixed(2)}x` : '—'}
                    </span>
                </div>
            </div>

            <StockPatternDetails patterns={patterns} currentPrice={tech.current_price} />
        </SectionCard>
    );
}

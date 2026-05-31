import { formatNumber, formatPercent } from '../../utils/api';

function prettyPatternName(pattern) {
    if (typeof pattern === 'string') return pattern.replace(/_/g, ' ');
    return pattern.name || pattern.pattern_name || pattern.type?.replace(/_/g, ' ') || 'Pattern';
}

function money(value) {
    return value == null ? 'N/A' : `$${formatNumber(value)}`;
}

function levelRows(pattern) {
    if (!pattern || typeof pattern !== 'object') return [];
    const rows = [
        ['Neckline', pattern.neckline],
        ['Support', pattern.support ?? pattern.support_current],
        ['Resistance', pattern.resistance ?? pattern.resistance_current],
        ['Breakout', pattern.breakout_level],
    ];
    return rows.filter(([, value]) => value != null);
}

export default function StockPatternDetails({ patterns = [], currentPrice }) {
    if (!patterns.length) {
        return (
            <div id="stock-pattern-details" style={{ marginTop: 'var(--spacing-md)', padding: 10, background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>No chart patterns detected in the current lookback.</div>
            </div>
        );
    }

    return (
        <div id="stock-pattern-details" style={{ marginTop: 'var(--spacing-md)', display: 'grid', gap: 8 }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--accent-yellow)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Pattern Detail
            </div>
            {patterns.map((rawPattern, index) => {
                const pattern = (rawPattern && typeof rawPattern === 'object') ? rawPattern : { type: String(rawPattern || 'pattern') };
                const target = pattern.target_price;
                const potential = target != null && currentPrice
                    ? ((Number(target) - Number(currentPrice)) / Number(currentPrice)) * 100
                    : null;
                const signal = pattern.signal || 'neutral';
                const rows = levelRows(pattern);
                return (
                    <div
                        key={`${pattern.type || pattern.pattern_type || 'pattern'}-${index}`}
                        style={{
                            background: signal === 'bearish' ? 'rgba(219,68,55,0.04)' : 'rgba(15,157,88,0.04)',
                            border: `1px solid ${signal === 'bearish' ? 'rgba(219,68,55,0.18)' : 'rgba(15,157,88,0.18)'}`,
                            borderRadius: 'var(--radius-md)',
                            padding: 10,
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
                            <div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'capitalize' }}>
                                    {prettyPatternName(pattern)}
                                </div>
                                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                                    {signal} setup / {pattern.confidence ?? 0}% confidence
                                </div>
                            </div>
                            <span className={`badge ${signal === 'bearish' ? 'badge-red' : 'badge-green'}`} style={{ fontSize: '0.62rem' }}>
                                {potential == null ? 'Target pending' : `${formatPercent(potential, true)} target`}
                            </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(92px, 1fr))', gap: 8, fontSize: '0.7rem' }}>
                            <div>
                                <div style={{ color: 'var(--text-muted)' }}>Current</div>
                                <strong style={{ fontFamily: 'var(--font-mono, monospace)' }}>{money(currentPrice)}</strong>
                            </div>
                            <div>
                                <div style={{ color: 'var(--text-muted)' }}>Target</div>
                                <strong style={{ fontFamily: 'var(--font-mono, monospace)' }}>{money(target)}</strong>
                            </div>
                            {rows.map(([label, value]) => (
                                <div key={label}>
                                    <div style={{ color: 'var(--text-muted)' }}>{label}</div>
                                    <strong style={{ fontFamily: 'var(--font-mono, monospace)' }}>{money(value)}</strong>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

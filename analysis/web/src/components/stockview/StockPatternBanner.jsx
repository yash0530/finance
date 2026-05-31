import { useEffect, useMemo, useState } from 'react';
import { getStockTechnicals, formatNumber, formatPercent } from '../../utils/api';

function patternName(pattern) {
    return pattern?.name || pattern?.pattern_name || pattern?.type?.replace(/_/g, ' ') || 'Pattern';
}

function money(value) {
    return value == null ? 'N/A' : `$${formatNumber(value)}`;
}

function confidenceClass(confidence) {
    if (confidence >= 70) return 'high';
    if (confidence >= 50) return 'medium';
    return 'low';
}

export default function StockPatternBanner({ ticker }) {
    const [patterns, setPatterns] = useState([]);
    const [currentPrice, setCurrentPrice] = useState(null);
    const [activeIndex, setActiveIndex] = useState(0);

    useEffect(() => {
        let cancelled = false;
        const id = window.setTimeout(() => {
            getStockTechnicals(ticker)
                .then(res => {
                    if (cancelled) return;
                    const data = res.data || {};
                    setPatterns(Array.isArray(data.patterns) ? data.patterns : []);
                    setCurrentPrice(data.current_price ?? null);
                    setActiveIndex(0);
                })
                .catch(() => {
                    if (!cancelled) {
                        setPatterns([]);
                        setCurrentPrice(null);
                    }
                });
        }, 0);

        return () => {
            cancelled = true;
            window.clearTimeout(id);
        };
    }, [ticker]);

    const pattern = patterns[activeIndex];
    const signal = pattern?.signal || 'neutral';
    const target = pattern?.target_price;
    const potential = useMemo(() => (
        target != null && currentPrice
            ? ((Number(target) - Number(currentPrice)) / Number(currentPrice)) * 100
            : null
    ), [currentPrice, target]);

    if (!pattern) return null;

    return (
        <section className={`stock-pattern-alert glass-card ${signal}`}>
            <div className="stock-pattern-alert-main">
                <div>
                    <div className="stock-pattern-kicker">{signal} pattern detected</div>
                    <h2>{patternName(pattern)}</h2>
                </div>
                <span className={`stock-pattern-confidence ${confidenceClass(pattern.confidence || 0)}`}>
                    {pattern.confidence || 0}% confidence
                </span>
            </div>

            {patterns.length > 1 && (
                <div className="stock-pattern-selector">
                    {patterns.map((p, index) => (
                        <button
                            key={`${p.type || p.pattern_type || 'pattern'}-${index}`}
                            className={index === activeIndex ? 'active' : ''}
                            onClick={() => setActiveIndex(index)}
                        >
                            {patternName(p)}
                        </button>
                    ))}
                </div>
            )}

            <div className="stock-pattern-levels">
                <div>
                    <span>Current</span>
                    <strong>{money(currentPrice)}</strong>
                </div>
                {pattern.neckline != null && (
                    <div>
                        <span>Neckline</span>
                        <strong>{money(pattern.neckline)}</strong>
                    </div>
                )}
                {(pattern.support ?? pattern.support_current) != null && (
                    <div>
                        <span>Support</span>
                        <strong>{money(pattern.support ?? pattern.support_current)}</strong>
                    </div>
                )}
                {(pattern.resistance ?? pattern.resistance_current) != null && (
                    <div>
                        <span>Resistance</span>
                        <strong>{money(pattern.resistance ?? pattern.resistance_current)}</strong>
                    </div>
                )}
                <div>
                    <span>Target</span>
                    <strong>{money(target)}</strong>
                </div>
                <div>
                    <span>Potential</span>
                    <strong className={potential == null ? '' : potential >= 0 ? 'value-positive' : 'value-negative'}>
                        {potential == null ? 'N/A' : formatPercent(potential, true)}
                    </strong>
                </div>
            </div>
        </section>
    );
}

import { useState, useEffect } from 'react';
import { getChart } from '../../utils/api';
import { formatPercent } from '../../utils/api';

/**
 * Phase 1 header: ticker + latest close + day change derived from the chart
 * endpoint (1m bars). Full fundamentals/mcap/sparkline land in Phase 3.
 */
export default function StockHeader({ ticker }) {
    const [last, setLast] = useState(null);
    const [changePct, setChangePct] = useState(null);

    useEffect(() => {
        let cancelled = false;
        if (!ticker) return;
        getChart(ticker, '5d').then(res => {
            if (cancelled) return;
            const bars = res.data?.bars || [];
            if (bars.length >= 2) {
                const latest = bars[bars.length - 1].close;
                const prev = bars[bars.length - 2].close;
                setLast(latest);
                if (prev) setChangePct((latest - prev) / prev * 100);
            } else if (bars.length === 1) {
                setLast(bars[0].close);
            }
        }).catch(() => {});
        return () => { cancelled = true; };
    }, [ticker]);

    const up = (changePct ?? 0) >= 0;

    return (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
            <h1 className="page-title" style={{ margin: 0, fontFamily: 'var(--font-mono, monospace)' }}>{ticker}</h1>
            {last != null && (
                <span style={{ fontSize: '1.2rem', fontWeight: 700 }}>${last.toFixed(2)}</span>
            )}
            {changePct != null && (
                <span style={{ fontSize: '0.9rem', color: up ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {formatPercent(changePct, true)}
                </span>
            )}
        </div>
    );
}

import { useState, useEffect } from 'react';
import { getStockHeader, formatCurrency, formatPercent } from '../../utils/api';

/**
 * Header: ticker, name, price, day move vs 52w range, market cap. Backed by the
 * fundamentals tool via /api/stock/<T>/header.
 */
export default function StockHeader({ ticker }) {
    const [d, setD] = useState(null);

    useEffect(() => {
        let cancelled = false;
        if (!ticker) return;
        getStockHeader(ticker).then(res => {
            if (!cancelled) setD(res.data || {});
        }).catch(() => {});
        return () => { cancelled = true; };
    }, [ticker]);

    const price = d?.current_price ?? d?.price;
    const target = d?.analyst_target;
    const upside = price && target ? (target - price) / price * 100 : null;
    const name = d?.name || d?.company_name;

    return (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, flexWrap: 'wrap' }}>
            <h1 className="page-title" style={{ margin: 0, fontFamily: 'var(--font-mono, monospace)' }}>{ticker}</h1>
            {name && <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{name}</span>}
            {price != null && <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>${Number(price).toFixed(2)}</span>}
            {d?.market_cap != null && (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{formatCurrency(d.market_cap)}</span>
            )}
            {upside != null && (
                <span style={{ fontSize: '0.8rem', color: upside >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {formatPercent(upside, true)} to target
                </span>
            )}
        </div>
    );
}

import { useState, useEffect } from 'react';
import { getStockFundamentals, formatCurrency, formatPercent, formatNumber } from '../../utils/api';
import SectionCard from './SectionCard';

function Metric({ label, value }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
            <span style={{ fontSize: '0.84rem', fontWeight: 600 }}>{value ?? 'N/A'}</span>
        </div>
    );
}

export default function FundamentalsCard({ ticker }) {
    const [fund, setFund] = useState(null);
    const [trends, setTrends] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getStockFundamentals(ticker).then(res => {
            if (cancelled) return;
            setFund(res.fundamentals?.data || {});
            setTrends(res.trends?.data || {});
        }).catch(e => !cancelled && setError(e.message))
          .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [ticker]);

    if (loading) return <SectionCard title="Key Fundamentals"><div className="loading-state" style={{ minHeight: 80 }}><div className="spinner spinner-sm" /></div></SectionCard>;
    if (error) return <SectionCard title="Key Fundamentals"><div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div></SectionCard>;

    const f = fund || {};
    const signal = trends?.trend_signals || trends?.signals;

    return (
        <SectionCard title="Key Fundamentals" id="section-fundamentals">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 'var(--spacing-md)' }}>
                <Metric label="Market Cap" value={f.market_cap != null ? formatCurrency(f.market_cap) : 'N/A'} />
                <Metric label="Fwd P/E" value={formatNumber(f.forward_pe)} />
                <Metric label="Trailing P/E" value={formatNumber(f.trailing_pe)} />
                <Metric label="Revenue" value={f.revenue != null ? formatCurrency(f.revenue) : 'N/A'} />
                <Metric label="Rev Growth" value={f.revenue_growth != null ? formatPercent(f.revenue_growth) : 'N/A'} />
                <Metric label="Profit Margin" value={f.profit_margin != null ? formatPercent(f.profit_margin) : 'N/A'} />
                <Metric label="52w High" value={f.week_52_high != null ? `$${formatNumber(f.week_52_high)}` : 'N/A'} />
                <Metric label="52w Low" value={f.week_52_low != null ? `$${formatNumber(f.week_52_low)}` : 'N/A'} />
                <Metric label="Analyst Tgt" value={f.analyst_target != null ? `$${formatNumber(f.analyst_target)}` : 'N/A'} />
            </div>
            {trends?.quarter_count > 0 && (
                <div style={{ marginTop: 'var(--spacing-md)', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {trends.quarter_count} quarters of trend data
                    {signal?.revenue_trend ? ` · revenue ${signal.revenue_trend}` : ''}
                    {signal?.margin_trend ? ` · margins ${signal.margin_trend}` : ''}
                </div>
            )}
        </SectionCard>
    );
}

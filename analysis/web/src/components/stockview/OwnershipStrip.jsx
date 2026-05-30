import { useState, useEffect } from 'react';
import { getStockOwnership, formatCurrency, formatPercent } from '../../utils/api';
import SectionCard from './SectionCard';

export default function OwnershipStrip({ ticker }) {
    const [inst, setInst] = useState(null);
    const [insider, setInsider] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getStockOwnership(ticker).then(res => {
            if (cancelled) return;
            setInst(res.institutional?.data || {});
            setInsider(res.insider?.data || {});
        }).catch(e => !cancelled && setError(e.message))
          .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [ticker]);

    if (loading) return <SectionCard title="Ownership & Insider"><div className="loading-state" style={{ minHeight: 80 }}><div className="spinner spinner-sm" /></div></SectionCard>;
    if (error) return <SectionCard title="Ownership & Insider"><div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div></SectionCard>;

    const holders = (inst?.top_holders || []).slice(0, 6);
    const buys = insider?.total_buys ?? 0;
    const sells = insider?.total_sells ?? 0;

    return (
        <SectionCard title="Ownership & Insider" id="section-ownership">
            <div style={{ display: 'flex', gap: 'var(--spacing-lg)', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 220 }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4 }}>
                        Top institutional holders
                        {inst?.total_institutional_pct != null ? ` · ${inst.total_institutional_pct}% inst. owned` : ''}
                    </div>
                    {holders.length === 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No holder data.</div>}
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                        {holders.map((h, i) => (
                            <li key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: '0.74rem', borderBottom: '1px solid var(--border-color)' }}>
                                <span>{h.name}{h.is_new ? <span className="badge badge-green" style={{ fontSize: '0.58rem', marginLeft: 6 }}>NEW</span> : ''}</span>
                                <span style={{ color: 'var(--text-muted)' }}>{h.value_usd ? formatCurrency(h.value_usd) : (h.pct_float != null ? formatPercent(h.pct_float, true) : '—')}</span>
                            </li>
                        ))}
                    </ul>
                </div>
                <div style={{ flex: 1, minWidth: 220 }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4 }}>Insider activity (90d)</div>
                    <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                        <span style={{ fontSize: '0.8rem' }}><span style={{ color: 'var(--accent-green)' }}>{buys}</span> buys</span>
                        <span style={{ fontSize: '0.8rem' }}><span style={{ color: 'var(--accent-red)' }}>{sells}</span> sells</span>
                        {insider?.clustered_buying && <span className="badge badge-green" style={{ fontSize: '0.6rem' }}>Clustered buying</span>}
                    </div>
                    {insider?.ceo_activity && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            CEO {insider.ceo_activity.type}: {insider.ceo_activity.shares?.toLocaleString()} sh
                            {insider.ceo_activity.value ? ` (${formatCurrency(insider.ceo_activity.value)})` : ''}
                        </div>
                    )}
                </div>
            </div>
        </SectionCard>
    );
}

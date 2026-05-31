import { useCallback, useEffect, useState } from 'react';
import { getCatalysts } from '../../utils/api';
import SectionCard from './SectionCard';

const TYPE_COLOR = {
    earnings: 'badge-blue',
    dividend: 'badge-green',
    FOMC: 'badge-purple',
    CPI: 'badge-yellow',
    NFP: 'badge-cyan',
};

export default function StockCatalysts({ ticker }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const res = await getCatalysts([ticker], 90);
            setItems(res.catalysts || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker]);

    useEffect(() => {
        const id = window.setTimeout(load, 0);
        return () => window.clearTimeout(id);
    }, [load]);

    const right = loading ? <span className="spinner spinner-sm" /> : null;

    return (
        <SectionCard title="Catalysts" id="section-stock-catalysts" right={right}>
            {error && <div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div>}
            {items.length === 0 && !loading && !error && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    No tracked catalysts in the next 90 days.
                </div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.slice(0, 8).map((c, i) => (
                    <li
                        key={`${c.ticker}-${c.event_type}-${c.event_date}-${i}`}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: 8,
                            padding: '5px 0',
                            borderBottom: '1px solid var(--border-color)',
                            fontSize: '0.74rem',
                        }}
                    >
                        <span className={`badge ${TYPE_COLOR[c.event_type] || 'badge-gray'}`} style={{ fontSize: '0.62rem' }}>
                            {c.event_type}
                        </span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', whiteSpace: 'nowrap' }}>
                            {c.event_date}
                        </span>
                    </li>
                ))}
            </ul>
        </SectionCard>
    );
}

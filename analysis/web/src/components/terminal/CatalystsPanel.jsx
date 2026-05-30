import { useState, useCallback, useEffect } from 'react';
import { getTerminalCatalysts } from '../../utils/api';
import PanelShell from './PanelShell';

const TYPE_COLOR = {
    earnings: 'badge-blue',
    dividend: 'badge-green',
    FOMC: 'badge-purple',
    CPI: 'badge-yellow',
    NFP: 'badge-cyan',
};

export default function CatalystsPanel({ onSelectTicker, area = 'catalysts' }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getTerminalCatalysts(7);
            setItems(res.items || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <PanelShell
            id="panel-catalysts"
            title="Fresh Catalysts"
            subtitle="next 7 days"
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            {items.length === 0 && !loading && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No catalysts in the next 7 days.</div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.map((c, i) => (
                    <li key={`${c.ticker}-${c.event_type}-${c.event_date}-${i}`} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '5px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.74rem',
                    }}>
                        <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <span className={`badge ${TYPE_COLOR[c.event_type] || 'badge-gray'}`} style={{ fontSize: '0.62rem' }}>
                                {c.event_type}
                            </span>
                            <button onClick={() => onSelectTicker(c.ticker)}
                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--text-primary)', fontFamily: 'var(--font-mono, monospace)', fontWeight: 600 }}>
                                {c.ticker}
                            </button>
                        </span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{c.event_date}</span>
                    </li>
                ))}
            </ul>
        </PanelShell>
    );
}

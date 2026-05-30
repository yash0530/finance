import { useState, useCallback, useEffect } from 'react';
import { getMovers } from '../../utils/api';
import { formatPercent } from '../../utils/api';
import PanelShell from './PanelShell';

function MoverRow({ row, onClick }) {
    const up = (row.change_pct ?? 0) >= 0;
    return (
        <button
            className="mover-row"
            onClick={() => onClick(row.ticker)}
            style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                width: '100%', padding: '5px 8px', background: 'transparent', border: 'none',
                borderBottom: '1px solid var(--border-color)', cursor: 'pointer',
                color: 'var(--text-primary)', fontSize: '0.78rem',
            }}
        >
            <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono, monospace)' }}>{row.ticker}</span>
            <span style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>{row.price != null ? `$${row.price}` : '—'}</span>
                <span style={{ color: up ? 'var(--accent-green)' : 'var(--accent-red)', minWidth: 64, textAlign: 'right' }}>
                    {row.change_pct != null ? formatPercent(row.change_pct, true) : '—'}
                </span>
            </span>
        </button>
    );
}

export default function MoversPanel({ onSelectTicker, area = 'movers' }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getMovers('themes', 10);
            setData(res.data);
            if (res.error && !(res.data?.gainers?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const gainers = data?.gainers || [];
    const losers = data?.losers || [];

    return (
        <PanelShell
            id="panel-movers"
            title="Movers"
            subtitle={data ? `${data.resolved}/${data.universe_size} resolved` : 'themes ∪ watchlist'}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--accent-green)', fontWeight: 700, marginBottom: 4 }}>GAINERS</div>
                    {gainers.length ? gainers.map(r => <MoverRow key={r.ticker} row={r} onClick={onSelectTicker} />)
                        : <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</div>}
                </div>
                <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--accent-red)', fontWeight: 700, marginBottom: 4 }}>LOSERS</div>
                    {losers.length ? losers.map(r => <MoverRow key={r.ticker} row={r} onClick={onSelectTicker} />)
                        : <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</div>}
                </div>
            </div>
        </PanelShell>
    );
}

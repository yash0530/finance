import { useState, useCallback, useEffect } from 'react';
import { getMovers } from '../../utils/api';
import { formatPercent } from '../../utils/api';
import PanelShell from './PanelShell';
import ResearchLink from '../ResearchLink';

function MoverRow({ row, onClick, onRunResearch }) {
    const up = (row.change_pct ?? 0) >= 0;
    return (
        <div
            className="mover-row"
            style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                width: '100%', padding: '5px 8px',
                borderBottom: '1px solid var(--border-color)',
                color: 'var(--text-primary)', fontSize: '0.78rem',
            }}
        >
            <button
                onClick={() => onClick(row.ticker)}
                style={{
                    background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                    fontWeight: 600, fontFamily: 'var(--font-mono, monospace)', color: 'inherit',
                }}
            >{row.ticker}</button>
            <span style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>{row.price != null ? `$${row.price}` : '—'}</span>
                <span style={{ color: up ? 'var(--accent-green)' : 'var(--accent-red)', minWidth: 64, textAlign: 'right' }}>
                    {row.change_pct != null ? formatPercent(row.change_pct, true) : '—'}
                </span>
                <ResearchLink ticker={row.ticker} onRunResearch={onRunResearch} />
            </span>
        </div>
    );
}

export default function MoversPanel({ onSelectTicker, onRunResearch, area = 'movers', initialResult = null, deferInitialLoad = false }) {
    const [data, setData] = useState(null);
    const [confidence, setConfidence] = useState('high');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getMovers('themes', 10);
            setData(res.data);
            setConfidence(res.confidence || 'high');
            if (res.error && !(res.data?.gainers?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!initialResult) return;
        setData(initialResult.data || null);
        setConfidence(initialResult.confidence || 'high');
        if (initialResult.error && !(initialResult.data?.gainers?.length)) setError(initialResult.error);
    }, [initialResult]);

    useEffect(() => {
        if (deferInitialLoad) return;
        load();
    }, [deferInitialLoad, load]);

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
            {confidence === 'low' && (
                <div className="alert alert-warning" style={{ fontSize: '0.72rem', padding: '6px 10px', marginBottom: 12, borderLeft: '3px solid var(--accent-yellow)' }}>
                    Sparse data: only {data?.resolved}/{data?.universe_size} tickers resolved. Data may be incomplete.
                </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--accent-green)', fontWeight: 700, marginBottom: 4 }}>GAINERS</div>
                    {gainers.length ? gainers.map(r => <MoverRow key={r.ticker} row={r} onClick={onSelectTicker} onRunResearch={onRunResearch} />)
                        : <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</div>}
                </div>
                <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--accent-red)', fontWeight: 700, marginBottom: 4 }}>LOSERS</div>
                    {losers.length ? losers.map(r => <MoverRow key={r.ticker} row={r} onClick={onSelectTicker} onRunResearch={onRunResearch} />)
                        : <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>—</div>}
                </div>
            </div>
        </PanelShell>
    );
}

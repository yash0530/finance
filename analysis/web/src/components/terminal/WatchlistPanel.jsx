import { useState, useCallback, useEffect } from 'react';
import { getTerminalWatchlist, addWatchlistTicker, removeWatchlistTicker, formatPercent } from '../../utils/api';
import PanelShell from './PanelShell';
import ResearchLink from '../ResearchLink';

export default function WatchlistPanel({ onSelectTicker, onRunResearch, area = 'watchlist' }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [newTicker, setNewTicker] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getTerminalWatchlist();
            setItems(res.items || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const add = useCallback(async (e) => {
        e.preventDefault();
        const t = newTicker.trim().toUpperCase();
        if (!t) return;
        try {
            await addWatchlistTicker(t);
            setNewTicker('');
            load();
        } catch (err) {
            setError(err.message);
        }
    }, [newTicker, load]);

    const remove = useCallback(async (t) => {
        try {
            await removeWatchlistTicker(t);
            load();
        } catch (err) {
            setError(err.message);
        }
    }, [load]);

    return (
        <PanelShell
            id="panel-watchlist"
            title="Watchlist"
            subtitle={`${items.length} tracked`}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            <form onSubmit={add} style={{ display: 'flex', gap: 6, marginBottom: 'var(--spacing-sm)' }}>
                <input
                    id="watchlist-add-input"
                    className="input"
                    placeholder="Add ticker…"
                    value={newTicker}
                    onChange={e => setNewTicker(e.target.value.toUpperCase())}
                    style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                />
                <button className="btn btn-secondary" type="submit" style={{ fontSize: '0.72rem', padding: '2px 10px' }}>Add</button>
            </form>
            {items.length === 0 && !loading && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Empty. Add tickers to track.</div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.map(it => {
                    const up = (it.change_pct ?? 0) >= 0;
                    return (
                        <li key={it.ticker} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '5px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.78rem',
                        }}>
                            <button
                                onClick={() => onSelectTicker(it.ticker)}
                                style={{
                                    background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                                    color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono, monospace)',
                                }}
                            >{it.ticker}</button>
                            <span style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                <span style={{ color: up ? 'var(--accent-green)' : 'var(--accent-red)', minWidth: 60, textAlign: 'right' }}>
                                    {it.change_pct != null ? formatPercent(it.change_pct, true) : '—'}
                                </span>
                                <ResearchLink ticker={it.ticker} onRunResearch={onRunResearch} />
                                <button
                                    onClick={() => remove(it.ticker)}
                                    title="Remove"
                                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.9rem' }}
                                >×</button>
                            </span>
                        </li>
                    );
                })}
            </ul>
        </PanelShell>
    );
}

import { useState, useEffect } from 'react';
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../utils/api';

export default function WatchlistPage({ onResearch }) {
    const [items, setItems]     = useState([]);
    const [ticker, setTicker]   = useState('');
    const [notes, setNotes]     = useState('');
    const [loading, setLoading] = useState(true);
    const [loaded, setLoaded]   = useState(false);
    const [adding, setAdding]   = useState(false);
    const [error, setError]     = useState('');

    async function load() {
        setError('');
        setLoaded(false);
        try {
            const data = await getWatchlist();
            setItems(data.data || []);
            setLoaded(true);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
    }

    useEffect(() => { load(); }, []);

    async function handleAdd(e) {
        e.preventDefault();
        if (!ticker.trim()) return;
        setAdding(true); setError('');
        try {
            await addToWatchlist(ticker.trim().toUpperCase(), notes);
            setTicker(''); setNotes('');
            await load();
        } catch (err) { setError(err.message); }
        finally { setAdding(false); }
    }

    async function handleRemove(t) {
        try {
            await removeFromWatchlist(t);
            setItems(prev => prev.filter(i => i.ticker !== t));
        } catch (err) { setError(err.message); }
    }

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Watchlist</h1>
                    <p className="page-subtitle">Track tickers you're monitoring</p>
                </div>
            </div>

            {/* Add form */}
            <form onSubmit={handleAdd} className="glass-card" style={{ marginBottom: 'var(--spacing-lg)', display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'flex-end' }}>
                <div className="input-group" style={{ width: 160 }}>
                    <label className="input-label">Ticker</label>
                    <input id="watchlist-ticker" className="input" placeholder="NVDA"
                        value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} />
                </div>
                <div className="input-group" style={{ flex: 1 }}>
                    <label className="input-label">Notes (optional)</label>
                    <input id="watchlist-notes" className="input" placeholder="Why you're watching…"
                        value={notes} onChange={e => setNotes(e.target.value)} />
                </div>
                <button id="btn-add-watchlist" className="btn btn-primary" type="submit" disabled={adding}>
                    {adding ? <span className="spinner spinner-sm" /> : '+ Add'}
                </button>
            </form>

            {error && <div className="alert alert-error" style={{ marginBottom: 'var(--spacing-md)' }}>{error}</div>}

            {loading ? (
                <div className="loading-state"><div className="spinner" /></div>
            ) : !loaded ? null : items.length === 0 ? (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">👁️</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>Watchlist is empty</h3>
                        <p style={{ fontSize: '0.825rem' }}>Add tickers above to start tracking them.</p>
                    </div>
                </div>
            ) : (
                <div className="glass-card">
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Notes</th>
                                    <th>Added</th>
                                    <th style={{ width: 100 }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items.map(item => (
                                    <tr key={item.ticker}>
                                        <td><span className="ticker-badge">{item.ticker}</span></td>
                                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                                            {item.notes || '—'}
                                        </td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                            {item.added_at ? new Date(item.added_at).toLocaleDateString() : '—'}
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 6 }}>
                                                <button
                                                    id={`btn-research-${item.ticker}`}
                                                    className="btn btn-secondary"
                                                    style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                                                    onClick={() => onResearch && onResearch(item.ticker)}
                                                    title="Research this ticker"
                                                >
                                                    🔬
                                                </button>
                                                <button
                                                    id={`btn-remove-${item.ticker}`}
                                                    className="btn btn-danger"
                                                    style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                                                    onClick={() => handleRemove(item.ticker)}
                                                    title="Remove from watchlist"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

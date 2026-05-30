import { useState, useEffect, useCallback } from 'react';
import { getThemes, createTheme, deleteTheme, getThemeTickers, addThemeTicker, removeThemeTicker } from '../../utils/api';

function ThemeCard({ theme, onChanged }) {
    const [tickers, setTickers] = useState(null);
    const [open, setOpen] = useState(false);
    const [newTicker, setNewTicker] = useState('');

    const loadTickers = useCallback(async () => {
        const res = await getThemeTickers(theme.slug);
        setTickers(res.tickers || []);
    }, [theme.slug]);

    const toggle = async () => {
        const next = !open;
        setOpen(next);
        if (next && tickers === null) await loadTickers();
    };

    const add = async (e) => {
        e.preventDefault();
        const t = newTicker.trim().toUpperCase();
        if (!t) return;
        await addThemeTicker(theme.slug, t);
        setNewTicker('');
        await loadTickers();
        onChanged?.();
    };

    const remove = async (t) => {
        await removeThemeTicker(theme.slug, t);
        await loadTickers();
        onChanged?.();
    };

    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button onClick={toggle} style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{theme.name}</span>
                    <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginLeft: 8 }}>{theme.slug} · {theme.ticker_count}</span>
                </button>
                <button className="btn btn-secondary" style={{ fontSize: '0.66rem', padding: '2px 8px' }}
                    onClick={async () => { await deleteTheme(theme.slug); onChanged?.(); }}>Delete</button>
            </div>
            {open && (
                <div style={{ marginTop: 'var(--spacing-sm)' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                        {(tickers || []).map(t => (
                            <span key={t.ticker} className="badge badge-gray" style={{ fontSize: '0.66rem', display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                                {t.ticker}
                                <button onClick={() => remove(t.ticker)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}>×</button>
                            </span>
                        ))}
                    </div>
                    <form onSubmit={add} style={{ display: 'flex', gap: 6 }}>
                        <input className="input" placeholder="Add ticker…" value={newTicker}
                            onChange={e => setNewTicker(e.target.value.toUpperCase())} style={{ maxWidth: 160, fontSize: '0.74rem', padding: '3px 8px' }} />
                        <button className="btn btn-secondary" type="submit" style={{ fontSize: '0.7rem', padding: '2px 10px' }}>Add</button>
                    </form>
                </div>
            )}
        </div>
    );
}

export default function ThemesEditor() {
    const [themes, setThemes] = useState([]);
    const [slug, setSlug] = useState('');
    const [name, setName] = useState('');

    const load = useCallback(async () => {
        try { setThemes((await getThemes()).themes || []); } catch { /* ignore */ }
    }, []);

    useEffect(() => { load(); }, [load]);

    const create = async (e) => {
        e.preventDefault();
        const s = slug.trim().toLowerCase().replace(/\s+/g, '-');
        const n = name.trim();
        if (!s || !n) return;
        await createTheme(s, n);
        setSlug(''); setName('');
        load();
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            <div className="glass-card" style={{ cursor: 'default' }}>
                <h3 style={{ fontSize: '0.95rem', margin: '0 0 8px 0' }}>Themes</h3>
                <form onSubmit={create} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <input className="input" placeholder="slug (e.g. quantum)" value={slug}
                        onChange={e => setSlug(e.target.value)} style={{ maxWidth: 160 }} />
                    <input className="input" placeholder="Name" value={name}
                        onChange={e => setName(e.target.value)} style={{ maxWidth: 200 }} />
                    <button className="btn btn-primary" type="submit" disabled={!slug.trim() || !name.trim()}>Create theme</button>
                </form>
            </div>
            {themes.map(t => <ThemeCard key={t.slug} theme={t} onChanged={load} />)}
        </div>
    );
}

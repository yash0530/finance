import { useState, useCallback, useEffect } from 'react';
import { getTerminalNews } from '../../utils/api';
import PanelShell from './PanelShell';

export default function NewsTape({ onSelectTicker, area = 'news-tape' }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getTerminalNews('all', 50);
            setItems(res.data?.items || []);
            if (res.error && !(res.data?.items?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <PanelShell
            id="panel-news"
            title="News Tape"
            subtitle={`${items.length} headlines`}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            {items.length === 0 && !loading && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    No headlines. Set FINNHUB_API_KEY for richer coverage.
                </div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.map((it, i) => (
                    <li key={`${it.url}-${i}`} style={{
                        padding: '6px 0', borderBottom: '1px solid var(--border-color)',
                        fontSize: '0.76rem', lineHeight: 1.4,
                    }}>
                        <span style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                            <button
                                onClick={() => onSelectTicker(it.ticker)}
                                style={{
                                    background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                                    color: 'var(--accent-blue-bright)', fontWeight: 700,
                                    fontFamily: 'var(--font-mono, monospace)', fontSize: '0.72rem', flexShrink: 0,
                                }}
                            >{it.ticker}</button>
                            <a href={it.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-primary)', textDecoration: 'none' }}>
                                {it.headline}
                            </a>
                        </span>
                        <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)' }}>
                            {it.source}{it.published_at ? ` · ${it.published_at}` : ''}
                        </span>
                    </li>
                ))}
            </ul>
        </PanelShell>
    );
}

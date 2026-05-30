import { useState, useEffect } from 'react';
import { getStockFilings, getTerminalNews } from '../../utils/api';
import SectionCard from './SectionCard';

/**
 * Merges recent SEC filings (free metadata) and news headlines into one
 * reverse-chronological timeline.
 */
export default function FilingsNewsTimeline({ ticker }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        Promise.allSettled([
            getStockFilings(ticker),
            getTerminalNews(ticker, 15),
        ]).then(([filingsRes, newsRes]) => {
            if (cancelled) return;
            const filings = (filingsRes.status === 'fulfilled' ? filingsRes.value.filings || [] : []).map(f => ({
                kind: 'filing', date: f.filing_date, label: f.form, url: f.url,
            }));
            const news = (newsRes.status === 'fulfilled' ? newsRes.value.data?.items || [] : []).map(n => ({
                kind: 'news', date: n.published_at, label: n.headline, url: n.url, source: n.source,
            }));
            const merged = [...filings, ...news]
                .filter(i => i.date)
                .sort((a, b) => String(b.date).localeCompare(String(a.date)));
            setItems(merged.slice(0, 25));
        }).catch(e => !cancelled && setError(e.message))
          .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [ticker]);

    if (loading) return <SectionCard title="Filings & News"><div className="loading-state" style={{ minHeight: 80 }}><div className="spinner spinner-sm" /></div></SectionCard>;
    if (error) return <SectionCard title="Filings & News"><div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div></SectionCard>;

    return (
        <SectionCard title="Filings & News" id="section-timeline">
            {items.length === 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No recent filings or news.</div>}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {items.map((it, i) => (
                    <li key={i} style={{ display: 'flex', gap: 10, alignItems: 'baseline', padding: '5px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.76rem' }}>
                        <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', minWidth: 78 }}>{it.date}</span>
                        <span className={`badge ${it.kind === 'filing' ? 'badge-purple' : 'badge-blue'}`} style={{ fontSize: '0.58rem', flexShrink: 0 }}>
                            {it.kind === 'filing' ? it.label : 'NEWS'}
                        </span>
                        <a href={it.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-primary)', textDecoration: 'none' }}>
                            {it.kind === 'filing' ? `SEC ${it.label}` : it.label}
                        </a>
                    </li>
                ))}
            </ul>
        </SectionCard>
    );
}

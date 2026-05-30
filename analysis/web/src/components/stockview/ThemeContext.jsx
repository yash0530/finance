import { useState, useEffect } from 'react';
import { getThemesByTicker } from '../../utils/api';
import SectionCard from './SectionCard';

/**
 * Theme / supply-chain context: which theme packs contain this ticker. Peer
 * cohort enrichment (peer_compare) is wired in the Console-driven reports;
 * here we surface membership so the user sees the ticker's place in the map.
 */
export default function ThemeContext({ ticker, onSelectTheme }) {
    const [themes, setThemes] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getThemesByTicker(ticker).then(res => {
            if (!cancelled) setThemes(res.themes || []);
        }).catch(() => {}).finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [ticker]);

    if (loading) return <SectionCard title="Theme Context"><div className="loading-state" style={{ minHeight: 60 }}><div className="spinner spinner-sm" /></div></SectionCard>;

    return (
        <SectionCard title="Theme Context" id="section-theme-context">
            {themes.length === 0 && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Not part of any theme pack. Add it from Settings → Themes.
                </div>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {themes.map(t => (
                    <button
                        key={t.slug}
                        className="badge badge-blue"
                        style={{ cursor: onSelectTheme ? 'pointer' : 'default', border: 'none', fontSize: '0.7rem' }}
                        onClick={() => onSelectTheme?.(t.slug)}
                        title={t.description || ''}
                    >{t.name}</button>
                ))}
            </div>
        </SectionCard>
    );
}

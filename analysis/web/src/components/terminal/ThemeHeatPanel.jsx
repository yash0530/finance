import { useState, useCallback, useEffect } from 'react';
import { getThemeHeat, formatPercent } from '../../utils/api';
import PanelShell from './PanelShell';

function HeatBar({ pct }) {
    if (pct == null) return <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>—</span>;
    const up = pct >= 0;
    const width = Math.min(100, Math.abs(pct) * 8);
    return (
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 120 }}>
            <span style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                <span style={{ display: 'block', height: '100%', width: `${width}%`, background: up ? 'var(--accent-green)' : 'var(--accent-red)' }} />
            </span>
            <span style={{ color: up ? 'var(--accent-green)' : 'var(--accent-red)', fontSize: '0.72rem', minWidth: 52, textAlign: 'right' }}>
                {formatPercent(pct, true)}
            </span>
        </span>
    );
}

export default function ThemeHeatPanel({ onSelectTicker, area = 'theme-heat' }) {
    const [themes, setThemes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [universe, setUniverse] = useState('themes');

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getThemeHeat(universe);
            setThemes(res.data?.themes || []);
            if (res.error && !(res.data?.themes?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [universe]);

    useEffect(() => { load(); }, [load]);

    const toggle = (
        <div style={{ display: 'flex', gap: 4 }}>
            {[['themes', 'My Themes'], ['sp500-sectors', 'S&P Sectors']].map(([id, label]) => (
                <button
                    key={id}
                    className={`btn ${universe === id ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.62rem', padding: '2px 7px' }}
                    onClick={() => setUniverse(id)}
                >{label}</button>
            ))}
        </div>
    );

    return (
        <PanelShell
            id="panel-theme-heat"
            title="Theme Heat"
            subtitle={universe === 'sp500-sectors' ? `${themes.length} S&P sectors` : `${themes.length} themes`}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
            actions={toggle}
        >
            {themes.length === 0 && !loading && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No themes defined.</div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {themes.map(t => (
                    <li key={t.slug} style={{ padding: '7px 0', borderBottom: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: '0.78rem', fontWeight: 600 }}>{t.name}</span>
                            <HeatBar pct={t.median_change_pct} />
                        </div>
                        {(t.leader || t.laggard) && (
                            <div style={{ display: 'flex', gap: 10, marginTop: 3, fontSize: '0.68rem' }}>
                                {t.leader && (
                                    <button onClick={() => onSelectTicker(t.leader.ticker)}
                                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--accent-green)', fontFamily: 'var(--font-mono, monospace)' }}>
                                        ▲ {t.leader.ticker} {formatPercent(t.leader.change_pct, true)}
                                    </button>
                                )}
                                {t.laggard && (
                                    <button onClick={() => onSelectTicker(t.laggard.ticker)}
                                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--accent-red)', fontFamily: 'var(--font-mono, monospace)' }}>
                                        ▼ {t.laggard.ticker} {formatPercent(t.laggard.change_pct, true)}
                                    </button>
                                )}
                            </div>
                        )}
                    </li>
                ))}
            </ul>
        </PanelShell>
    );
}

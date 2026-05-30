import { useState, useEffect, useCallback } from 'react';
import { runScreener, getSavedScreeners, saveScreener, deleteSavedScreener } from '../utils/api';
import RulesBuilder from '../components/screener/RulesBuilder';
import ResultsTable from '../components/screener/ResultsTable';

const DEFAULT_SPEC = {
    universe: 'themes',
    combine: 'AND',
    rules: [
        { field: 'rsi', op: '<', value: 30 },
        { field: 'yoy_revenue_growth', op: '>', value: 0.20 },
    ],
};

/**
 * Screener — rule-based screening over cached tool data, with saved configs.
 */
export default function ScreenerPage({ onSelectTicker, presetName }) {
    const [spec, setSpec] = useState(DEFAULT_SPEC);
    const [result, setResult] = useState(null);
    const [running, setRunning] = useState(false);
    const [saved, setSaved] = useState([]);
    const [name, setName] = useState('');

    const loadSaved = useCallback(async () => {
        try {
            const rows = (await getSavedScreeners()).saved || [];
            setSaved(rows);
            return rows;
        } catch { return []; }
    }, []);

    const runSpec = useCallback(async (s) => {
        setRunning(true);
        setResult(null);
        try {
            setResult(await runScreener(s));
        } catch (e) {
            setResult({ error: e.message });
        } finally {
            setRunning(false);
        }
    }, []);

    const run = useCallback(() => runSpec(spec), [runSpec, spec]);

    const loadAndRun = useCallback((s) => {
        const next = { universe: 'themes', combine: 'AND', rules: [], ...s };
        setSpec(next);
        runSpec(next);
    }, [runSpec]);

    useEffect(() => { loadSaved(); }, [loadSaved]);

    // Deep-link from the sidebar Market shortcut: load + auto-run a named preset.
    useEffect(() => {
        if (!presetName) return;
        let cancelled = false;
        loadSaved().then(rows => {
            if (cancelled) return;
            const match = rows.find(s => s.name === presetName);
            if (match) loadAndRun(match.rules);
        });
        return () => { cancelled = true; };
    }, [presetName, loadSaved, loadAndRun]);

    const save = useCallback(async () => {
        const n = name.trim();
        if (!n) return;
        await saveScreener(n, spec);
        setName('');
        loadSaved();
    }, [name, spec, loadSaved]);

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Screener</h1>
                    <p className="page-subtitle">Rule-based screening over cached tool data</p>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 'var(--spacing-lg)', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 360, display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                    <RulesBuilder spec={spec} onChange={setSpec} onRun={run} running={running} />
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input className="input" placeholder="Save this screen as…" value={name}
                            onChange={e => setName(e.target.value)} style={{ maxWidth: 240 }} />
                        <button className="btn btn-secondary" onClick={save} disabled={!name.trim()}>Save</button>
                    </div>
                    <ResultsTable result={result} onSelectTicker={onSelectTicker} />
                </div>

                <aside className="glass-card" style={{ cursor: 'default', minWidth: 200 }}>
                    <h4 style={{ fontSize: '0.78rem', margin: '0 0 8px 0', color: 'var(--text-secondary)' }}>Saved screens</h4>
                    {saved.length === 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>None saved.</div>}
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                        {saved.map(s => (
                            <li key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--border-color)' }}>
                                <button onClick={() => loadAndRun(s.rules)}
                                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--accent-blue-bright)', fontSize: '0.74rem', textAlign: 'left' }}>
                                    {s.name}
                                </button>
                                <button onClick={async () => { await deleteSavedScreener(s.id); loadSaved(); }}
                                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
                            </li>
                        ))}
                    </ul>
                </aside>
            </div>
        </div>
    );
}

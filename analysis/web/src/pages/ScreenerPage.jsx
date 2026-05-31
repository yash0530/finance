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

async function fetchSavedScreeners() {
    const rows = (await getSavedScreeners()).saved || [];
    return rows;
}

/**
 * Screener — rule-based screening over cached tool data, with saved configs.
 */
export default function ScreenerPage({ onSelectTicker, onRunResearch, presetName }) {
    const [spec, setSpec] = useState(DEFAULT_SPEC);
    const [result, setResult] = useState(null);
    const [running, setRunning] = useState(false);
    const [saved, setSaved] = useState([]);
    const [name, setName] = useState('');

    const refreshSaved = useCallback(async () => {
        try {
            const rows = await fetchSavedScreeners();
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

    useEffect(() => {
        if (presetName) return undefined;
        let cancelled = false;
        fetchSavedScreeners()
            .then(rows => { if (!cancelled) setSaved(rows); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [presetName]);

    // Deep-link from Market action buttons: load + auto-run a named preset.
    useEffect(() => {
        if (!presetName) return;
        let cancelled = false;
        fetchSavedScreeners()
            .then(rows => {
                if (cancelled) return;
                setSaved(rows);
                const match = rows.find(s => s.name === presetName);
                if (match) loadAndRun(match.rules);
            })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [presetName, loadAndRun]);

    const save = useCallback(async () => {
        const n = name.trim();
        if (!n) return;
        await saveScreener(n, spec);
        setName('');
        await refreshSaved();
    }, [name, spec, refreshSaved]);

    return (
        <div className="fade-in screener-page">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Screener</h1>
                    <p className="page-subtitle">Rule-based screening over cached tool data</p>
                </div>
            </div>

            <div className="screener-layout">
                <div className="screener-main">
                    <RulesBuilder spec={spec} onChange={setSpec} onRun={run} running={running} />
                    <div className="screener-save-row">
                        <input className="input" placeholder="Save this screen as…" value={name}
                            onChange={e => setName(e.target.value)} />
                        <button className="btn btn-secondary" onClick={save} disabled={!name.trim()}>Save</button>
                    </div>
                    <ResultsTable result={result} onSelectTicker={onSelectTicker} onRunResearch={onRunResearch} />
                </div>

                <aside className="glass-card screener-saved-panel">
                    <h4 className="screener-saved-title">Saved screens</h4>
                    {saved.length === 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>None saved.</div>}
                    <ul className="screener-saved-list">
                        {saved.map(s => (
                            <li key={s.id} className="screener-saved-item">
                                <button onClick={() => loadAndRun(s.rules)}
                                    className="screener-saved-name"
                                    title={s.name}>
                                    {s.name}
                                </button>
                                <button onClick={async () => { await deleteSavedScreener(s.id); await refreshSaved(); }}
                                    className="screener-saved-delete"
                                    type="button"
                                    title={`Delete ${s.name}`}
                                    aria-label="Delete saved screen">×</button>
                            </li>
                        ))}
                    </ul>
                </aside>
            </div>
        </div>
    );
}

import { useState, useCallback, useEffect } from 'react';
import { getTerminalWatchlist, generateHypothesis } from '../../utils/api';
import PanelShell from './PanelShell';

function HypothesisRow({ ticker, onSelectTicker }) {
    const [take, setTake] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const generate = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await generateHypothesis(ticker);
            setTake(res);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker]);

    return (
        <li style={{ padding: '7px 0', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button onClick={() => onSelectTicker(ticker)}
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono, monospace)', fontSize: '0.78rem' }}>
                    {ticker}
                </button>
                <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.68rem', padding: '2px 8px' }}
                    onClick={generate}
                    disabled={loading}
                    title="~$0.05 per generation, cached 4h"
                >
                    {loading ? <span className="spinner spinner-sm" /> : (take ? 'Regenerate' : 'Generate')}
                </button>
            </div>
            {error && <div style={{ fontSize: '0.7rem', color: 'var(--accent-red)', marginTop: 4 }}>{error}</div>}
            {take && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: 5, lineHeight: 1.5 }}>
                    {take.why_md}
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: 3 }}>
                        {take.cached ? 'cached' : `$${Number(take.cost_usd || 0).toFixed(3)}`}
                        {take.evidence_refs?.length ? ` · ${take.evidence_refs.join(', ')}` : ''}
                    </div>
                </div>
            )}
        </li>
    );
}

export default function HypothesesPanel({ onSelectTicker, area = 'hypotheses' }) {
    const [tickers, setTickers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getTerminalWatchlist();
            setTickers((res.items || []).map(i => i.ticker));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <PanelShell
            id="panel-hypotheses"
            title="Hypotheses"
            subtitle="AI on demand · ~$0.05/click"
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            {tickers.length === 0 && !loading && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Add watchlist tickers to generate quick reads.
                </div>
            )}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {tickers.map(t => <HypothesisRow key={t} ticker={t} onSelectTicker={onSelectTicker} />)}
            </ul>
        </PanelShell>
    );
}

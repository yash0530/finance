import { useCallback, useState } from 'react';
import { generateHypothesis } from '../../utils/api';
import SectionCard from './SectionCard';

export default function StockQuickTake({ ticker }) {
    const [take, setTake] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async (refresh = false) => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            setTake(await generateHypothesis(ticker, refresh));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker]);

    const right = (
        <button
            className="btn btn-secondary"
            style={{ fontSize: '0.68rem', padding: '2px 8px', minHeight: 26 }}
            onClick={() => load(Boolean(take))}
            disabled={loading}
            title="Cached for 4 hours when available"
        >
            {loading ? <span className="spinner spinner-sm" /> : (take ? 'Refresh' : 'Generate')}
        </button>
    );

    return (
        <SectionCard title="Quick Take" id="section-quick-take" right={right}>
            {error && <div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div>}
            {!take && !error && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
                    Generate the cached three-sentence view when you want LLM spend.
                </div>
            )}
            {take && (
                <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                    {take.why_md}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                        <span className={`badge ${take.cached ? 'badge-gray' : 'badge-green'}`} style={{ fontSize: '0.58rem' }}>
                            {take.cached ? 'cached' : 'fresh'}
                        </span>
                        {!take.cached && (
                            <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)' }}>
                                ${Number(take.cost_usd || 0).toFixed(3)}
                            </span>
                        )}
                        {take.evidence_refs?.length > 0 && (
                            <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)' }}>
                                {take.evidence_refs.join(', ')}
                            </span>
                        )}
                    </div>
                </div>
            )}
        </SectionCard>
    );
}

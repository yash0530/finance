import { useState, useCallback, useEffect } from 'react';
import { getFlow } from '../../utils/api';
import PanelShell from './PanelShell';

/**
 * Flow Snapshot. On the free tier (no UNUSUAL_WHALES_API_KEY) the backend
 * returns {degraded:true} and we render a sparse state explaining the upgrade
 * path. With a key, the panel shows the options_flow payload.
 */
export default function FlowPanel({ area = 'flow', ticker = '', initialStatus = null }) {
    const [payload, setPayload] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            setPayload(await getFlow(ticker));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker]);

    useEffect(() => {
        if (!ticker) return undefined;
        const id = window.setTimeout(load, 0);
        return () => window.clearTimeout(id);
    }, [load, ticker]);

    useEffect(() => {
        if (ticker || !initialStatus) return;
        setPayload({
            degraded: initialStatus.status !== 'available',
            reason: initialStatus.message,
            free_tier: initialStatus.provider,
        });
    }, [initialStatus, ticker]);

    const degraded = payload?.degraded;

    return (
        <PanelShell
            id="panel-flow"
            title={ticker ? `${ticker} Flow` : 'Flow Snapshot'}
            subtitle={degraded ? 'degraded' : (ticker ? 'options flow' : 'market-wide')}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
            {!ticker && !payload && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <div>Flow is on demand to protect provider quotas.</div>
                    <div style={{ fontSize: '0.7rem', marginTop: 4 }}>Open a ticker in Stock View, or refresh here to check provider availability.</div>
                </div>
            )}
            {degraded && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <div style={{ marginBottom: 6 }}>{payload.reason}</div>
                    <div style={{ fontSize: '0.7rem' }}>{payload.free_tier}</div>
                    <div style={{ marginTop: 8 }}>
                        <span className="badge badge-yellow" style={{ fontSize: '0.62rem' }}>Add UNUSUAL_WHALES_API_KEY to unlock</span>
                    </div>
                </div>
            )}
            {!degraded && payload && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    {payload.note || (ticker ? 'No notable flow returned for this ticker.' : 'Provide a ticker via Stock View for a flow snapshot.')}
                </div>
            )}
        </PanelShell>
    );
}

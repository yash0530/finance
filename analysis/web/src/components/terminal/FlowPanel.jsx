import { useState, useCallback, useEffect } from 'react';
import { getFlow } from '../../utils/api';
import PanelShell from './PanelShell';

/**
 * Flow Snapshot. On the free tier (no UNUSUAL_WHALES_API_KEY) the backend
 * returns {degraded:true} and we render a sparse state explaining the upgrade
 * path. With a key, the panel shows the options_flow payload.
 */
export default function FlowPanel({ area = 'flow' }) {
    const [payload, setPayload] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            setPayload(await getFlow());
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const degraded = payload?.degraded;

    return (
        <PanelShell
            id="panel-flow"
            title="Flow Snapshot"
            subtitle={degraded ? 'degraded' : 'options flow'}
            area={area}
            onRefresh={load}
            loading={loading}
            error={error}
        >
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
                    {payload.note || 'Provide a ticker via Stock View for a flow snapshot.'}
                </div>
            )}
        </PanelShell>
    );
}

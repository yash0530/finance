import { useState, useCallback, useEffect } from 'react';
import { getFlow } from '../../utils/api';
import PanelShell from './PanelShell';

function fmtNumber(value, digits = 2) {
    if (value == null || Number.isNaN(Number(value))) return '-';
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function fmtPct(value) {
    if (value == null || Number.isNaN(Number(value))) return '-';
    return `${(Number(value) * 100).toFixed(1)}%`;
}

function FlowMetrics({ data }) {
    if (!data || Object.keys(data).length === 0) return null;
    const unusual = data.unusual_contracts || [];
    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.72rem' }}>
            <Metric label="ATM IV" value={fmtPct(data.atm_iv)} />
            <Metric label="P/C OI" value={fmtNumber(data.put_call_ratio_oi)} />
            <Metric label="P/C Vol" value={fmtNumber(data.put_call_ratio_volume)} />
            <Metric label="Net Prem" value={`$${fmtNumber(data.net_premium_proxy, 0)}`} />
            <Metric label="Skew" value={fmtNumber(data.skew_proxy)} />
            <Metric label="Unusual" value={String(unusual.length)} />
        </div>
    );
}

function Metric({ label, value }) {
    return (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: 6, padding: '5px 7px', minWidth: 0 }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.62rem' }}>{label}</div>
            <div style={{ color: 'var(--text-primary)', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
        </div>
    );
}

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
    const metrics = payload?.data;

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
                    <div style={{ marginTop: 8, marginBottom: metrics ? 8 : 0 }}>
                        <span className="badge badge-yellow" style={{ fontSize: '0.62rem' }}>Add UNUSUAL_WHALES_API_KEY to unlock</span>
                    </div>
                    <FlowMetrics data={metrics} />
                </div>
            )}
            {!degraded && payload && (
                <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    {metrics ? <FlowMetrics data={metrics} /> : (payload.note || (ticker ? 'No notable flow returned for this ticker.' : 'Provide a ticker via Stock View for a flow snapshot.'))}
                </div>
            )}
        </PanelShell>
    );
}

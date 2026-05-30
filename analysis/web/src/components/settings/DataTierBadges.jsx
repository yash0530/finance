import { useState, useEffect } from 'react';
import { getDataTier, refreshSp500Snapshot } from '../../utils/api';

/**
 * Renders the live data-tier badges from os.environ on the backend. No secrets
 * are returned — only which env keys are present.
 */
export default function DataTierBadges() {
    const [tiers, setTiers] = useState([]);
    const [optional, setOptional] = useState({});
    const [snapshot, setSnapshot] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [message, setMessage] = useState(null);

    async function loadStatus() {
        return getDataTier().then(res => {
            setTiers(res.tiers || []);
            setOptional(res.optional_keys || {});
            setSnapshot(res.sp500_snapshot || null);
        }).catch(() => {});
    }

    useEffect(() => {
        loadStatus();
    }, []);

    async function handleRefresh() {
        setRefreshing(true);
        setMessage(null);
        try {
            const res = await refreshSp500Snapshot();
            const data = res.result?.data || {};
            setSnapshot({
                exists: true,
                timestamp: data.timestamp,
                row_count: data.row_count,
                age_seconds: 0,
            });
            setMessage({ type: 'success', text: `Refreshed ${data.row_count || 0} constituents` });
        } catch (err) {
            setMessage({ type: 'error', text: err.message });
        } finally {
            setRefreshing(false);
        }
    }

    function formatAge(seconds) {
        if (seconds == null) return 'unknown age';
        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m old`;
        const hours = Math.floor(minutes / 60);
        if (hours < 48) return `${hours}h old`;
        return `${Math.floor(hours / 24)}d old`;
    }

    function formatTimestamp(ts) {
        if (!ts) return 'No snapshot found';
        const d = new Date(ts);
        if (Number.isNaN(d.getTime())) return ts;
        return d.toLocaleString();
    }

    return (
        <div className="glass-card" style={{ cursor: 'default', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
            <div>
                <h3 style={{ fontSize: '0.95rem', margin: '0 0 4px 0' }}>Data tiers</h3>
                <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: 0, marginBottom: 0 }}>
                    Live tiers are detected from environment keys at boot. Paid integrations enrich existing tools — no code changes needed.
                </p>
            </div>
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--spacing-md)',
                padding: '10px 12px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-color)', flexWrap: 'wrap',
            }}>
                <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>S&amp;P 500 snapshot</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        {formatTimestamp(snapshot?.timestamp)} · {snapshot?.row_count || 0} rows · {formatAge(snapshot?.age_seconds)}
                    </div>
                </div>
                <button
                    id="btn-refresh-sp500"
                    className="btn btn-secondary"
                    type="button"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    title="Refresh S&P 500 snapshot"
                >
                    {refreshing ? <><span className="spinner spinner-sm" /> Refreshing...</> : 'Refresh'}
                </button>
            </div>
            {message && (
                <div className={`alert alert-${message.type}`} style={{ margin: 0 }}>{message.text}</div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                {tiers.map(t => (
                    <div key={t.id} style={{
                        display: 'flex', alignItems: 'center', gap: 12, padding: '8px 10px',
                        borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)',
                        border: `1px solid ${t.active ? 'var(--accent-green)' : 'var(--border-color)'}`,
                    }}>
                        <span className={`badge ${t.active ? 'badge-green' : 'badge-gray'}`} style={{ fontSize: '0.62rem', flexShrink: 0 }}>
                            {t.active ? 'LIVE' : 'off'}
                        </span>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{t.label}</div>
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{t.unlocks}</div>
                        </div>
                        {t.env && !t.active && (
                            <code style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>set {t.env}</code>
                        )}
                    </div>
                ))}
            </div>
            <div style={{ marginTop: 'var(--spacing-sm)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(optional).map(([k, v]) => (
                    <span key={k} className={`badge ${v ? 'badge-green' : 'badge-gray'}`} style={{ fontSize: '0.6rem' }}>
                        {k}: {v ? 'set' : 'unset'}
                    </span>
                ))}
            </div>
        </div>
    );
}

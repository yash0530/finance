import { useState, useEffect } from 'react';
import { getDataTier } from '../../utils/api';

/**
 * Renders the live data-tier badges from os.environ on the backend. No secrets
 * are returned — only which env keys are present.
 */
export default function DataTierBadges() {
    const [tiers, setTiers] = useState([]);
    const [optional, setOptional] = useState({});

    useEffect(() => {
        getDataTier().then(res => {
            setTiers(res.tiers || []);
            setOptional(res.optional_keys || {});
        }).catch(() => {});
    }, []);

    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <h3 style={{ fontSize: '0.95rem', margin: '0 0 4px 0' }}>Data tiers</h3>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: 0 }}>
                Live tiers are detected from environment keys at boot. Paid integrations enrich existing tools — no code changes needed.
            </p>
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

import React, { useState } from 'react';
import { acceptStagedMemo, discardStagedMemo } from '../utils/api';

/**
 * Living Memo delta panel — shows new version + delta summary.
 */
export default function MemoDeltaPanel({ delta, ticker }) {
    const [status, setStatus] = useState(null);
    const [busy, setBusy] = useState(false);
    if (!delta) return null;

    async function act(kind) {
        if (!ticker) return;
        setBusy(true);
        setStatus(null);
        try {
            const res = kind === 'accept'
                ? await acceptStagedMemo(ticker)
                : await discardStagedMemo(ticker);
            setStatus({
                type: 'success',
                text: kind === 'accept'
                    ? `Memo accepted as v${res.new_version}`
                    : 'Memo update discarded',
            });
        } catch (err) {
            setStatus({ type: 'error', text: err.message });
        } finally {
            setBusy(false);
        }
    }

    return (
        <details className="glass-card fade-in" style={{ padding: 'var(--spacing-md)', borderColor: 'rgba(124, 58, 237, 0.3)' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)', outline: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>Living Memo Update</span>
                {delta.new_version && <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>v{delta.new_version}</span>}
                {delta.staged && <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>staged</span>}
            </summary>
            <div style={{ marginTop: 'var(--spacing-md)' }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {delta.delta_summary || 'No summary available'}
                </div>
                {ticker && delta.staged && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                        <button className="btn btn-primary" type="button" disabled={busy || status?.type === 'success'} onClick={() => act('accept')}>
                            {busy ? <><span className="spinner spinner-sm" /> Saving...</> : 'Accept memo update'}
                        </button>
                        <button className="btn btn-secondary" type="button" disabled={busy || status?.type === 'success'} onClick={() => act('discard')}>
                            Discard
                        </button>
                    </div>
                )}
                {status && (
                    <div className={`alert alert-${status.type}`} style={{ fontSize: '0.75rem', marginTop: 8 }}>{status.text}</div>
                )}
                {delta.error && (
                    <div className="alert alert-warning" style={{ fontSize: '0.75rem', marginTop: 8 }}>{delta.error}</div>
                )}
                {delta.new_memo && (
                    <details style={{ marginTop: 10 }}>
                        <summary style={{ fontSize: '0.72rem', color: 'var(--text-muted)', cursor: 'pointer' }}>View memo content</summary>
                        <pre style={{ fontSize: '0.68rem', maxHeight: 300, overflow: 'auto', background: 'var(--bg-secondary)', padding: 8, borderRadius: 4, marginTop: 6 }}>
                            {JSON.stringify(delta.new_memo, null, 2)}
                        </pre>
                    </details>
                )}
            </div>
        </details>
    );
}

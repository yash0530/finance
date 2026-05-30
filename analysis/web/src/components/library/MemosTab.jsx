import { useState, useEffect, useCallback } from 'react';
import { getLibraryMemos, getMemo } from '../../utils/api';

function formatDate(iso) {
    if (!iso) return 'Unknown';
    return new Date(iso).toLocaleString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
}

function MemoDetail({ ticker, onBack }) {
    const [memo, setMemo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getMemo(ticker).then(res => {
            if (!cancelled) setMemo(res);
        }).catch(e => !cancelled && setError(e.message))
          .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [ticker]);

    const sections = memo?.content_json ? Object.entries(memo.content_json) : [];

    return (
        <div className="fade-in">
            <button className="btn btn-secondary" style={{ marginBottom: 'var(--spacing-md)' }} onClick={onBack}>← Back to memos</button>
            <h2 style={{ fontFamily: 'var(--font-mono, monospace)' }}>{ticker} Living Memo {memo?.current_version ? `· v${memo.current_version}` : ''}</h2>
            {loading && <div className="loading-state"><div className="spinner" /></div>}
            {error && <div className="alert alert-error">{error}</div>}
            {!loading && sections.length === 0 && <div style={{ color: 'var(--text-muted)' }}>No memo sections.</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                {sections.map(([key, section]) => {
                    const body = typeof section === 'object' ? (section.content_md || '') : String(section);
                    const conf = typeof section === 'object' ? section.confidence : null;
                    return (
                        <div key={key} className="glass-card" style={{ cursor: 'default' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                <h4 style={{ margin: 0, fontSize: '0.82rem', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</h4>
                                {conf && <span className="badge badge-gray" style={{ fontSize: '0.6rem' }}>{conf}</span>}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line', lineHeight: 1.6 }}>{body || '—'}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function MemosTab() {
    const [memos, setMemos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selected, setSelected] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getLibraryMemos();
            setMemos(res.memos || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    if (selected) return <MemoDetail ticker={selected} onBack={() => setSelected(null)} />;

    if (loading) return <div className="loading-state"><div className="spinner" /></div>;
    if (error) return <div className="alert alert-error">{error}</div>;

    if (memos.length === 0) {
        return (
            <div className="glass-card" style={{ cursor: 'default' }}>
                <div className="empty-state">
                    <h3 style={{ color: 'var(--text-secondary)' }}>No Living Memos yet</h3>
                    <p style={{ fontSize: '0.825rem' }}>Run <code>/thesis &lt;T&gt;</code> in the Console to build a ticker's memo.</p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--spacing-md)' }}>
            {memos.map(m => (
                <button
                    key={m.ticker}
                    className="glass-card"
                    onClick={() => setSelected(m.ticker)}
                    style={{ textAlign: 'left', border: '1px solid var(--border-color)', cursor: 'pointer' }}
                >
                    <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', fontSize: '0.95rem' }}>{m.ticker}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                        v{m.current_version} · {formatDate(m.updated_at)}
                    </div>
                </button>
            ))}
        </div>
    );
}

/**
 * RunHistoryRail — recent commands run this session. Phase 1 keeps history in
 * memory; Phase 4 wires it to persisted reports.
 */
export default function RunHistoryRail({ history, onReplay }) {
    return (
        <aside className="glass-card" style={{ cursor: 'default', minWidth: 200 }}>
            <h4 style={{ fontSize: '0.78rem', margin: '0 0 8px 0', color: 'var(--text-secondary)' }}>Run history</h4>
            {history.length === 0 && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No runs yet.</div>}
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {history.map((h, i) => (
                    <li key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--border-color)' }}>
                        <button
                            onClick={() => onReplay(h.command)}
                            style={{
                                background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                                color: 'var(--accent-blue-bright)', fontFamily: 'var(--font-mono, monospace)', fontSize: '0.72rem',
                                textAlign: 'left', width: '100%',
                            }}
                        >{h.command}</button>
                        <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>{h.status}</span>
                    </li>
                ))}
            </ul>
        </aside>
    );
}

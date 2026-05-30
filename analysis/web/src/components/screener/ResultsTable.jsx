export default function ResultsTable({ result, onSelectTicker }) {
    if (!result) return null;
    if (result.needs_scan) {
        return (
            <div className="alert alert-warning" style={{ fontSize: '0.78rem' }}>
                {result.message || 'Technical/pattern rules over the S&P 500 need a live scan.'}
                {' '}Enable the <strong>scan (slow)</strong> toggle above and re-run.
            </div>
        );
    }
    if (result.error) {
        return <div className="alert alert-error" style={{ fontSize: '0.78rem' }}>{result.error}</div>;
    }
    const matches = result.matches || [];
    const fields = (result.rules || []).map(r => r.field);

    return (
        <div className="glass-card" id="screener-results" style={{ cursor: 'default' }}>
            {result.scan_limited && (
                <div className="alert alert-warning" style={{ fontSize: '0.74rem', marginBottom: 'var(--spacing-sm)' }}>
                    {result.message}
                </div>
            )}
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: 'var(--spacing-sm)' }}>
                {result.matched ?? matches.length} matched of {result.evaluated} evaluated
            </div>
            {matches.length === 0 ? (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>No tickers matched these rules.</div>
            ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                        <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                            <th style={{ padding: '4px 8px' }}>Ticker</th>
                            {fields.map(f => <th key={f} style={{ padding: '4px 8px' }}>{f}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {matches.map(m => (
                            <tr key={m.ticker} style={{ borderTop: '1px solid var(--border-color)' }}>
                                <td style={{ padding: '4px 8px', display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <button onClick={() => onSelectTicker(m.ticker)}
                                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--accent-blue-bright)', fontWeight: 600, fontFamily: 'var(--font-mono, monospace)' }}>
                                        {m.ticker}
                                    </button>
                                    {m.partial && (
                                        <span className="badge badge-gray" style={{ fontSize: '0.55rem', padding: '1px 4px', opacity: 0.8 }} title={`Missing fields: ${m.missing_fields?.join(', ')}`}>
                                            partial
                                        </span>
                                    )}
                                </td>
                                {fields.map(f => (
                                    <td key={f} style={{ padding: '4px 8px', color: 'var(--text-secondary)' }}>
                                        {formatValue(m.values?.[f])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}

function formatValue(v) {
    if (v == null) return '—';
    if (typeof v === 'boolean') return v ? 'Yes' : 'No';
    if (typeof v === 'number') return Number.isInteger(v) ? v : v.toFixed(2);
    return String(v);
}

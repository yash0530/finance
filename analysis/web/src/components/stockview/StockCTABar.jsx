/**
 * CTA bar — deep-links into the Console with a slash command pre-filled.
 * onRunCommand(command) is handled by App, which navigates to #console and
 * seeds the command bar.
 */
export default function StockCTABar({ ticker, onRunCommand }) {
    const actions = [
        { cmd: `/thesis ${ticker}`, label: 'Run thesis', primary: true },
        { cmd: `/why ${ticker}`, label: 'Quick why' },
        { cmd: `/dossier ${ticker}`, label: 'Deep dossier' },
    ];
    return (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {actions.map(a => (
                <button
                    key={a.cmd}
                    id={`cta-${a.label.toLowerCase().replace(/\s+/g, '-')}`}
                    className={`btn ${a.primary ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.78rem' }}
                    onClick={() => onRunCommand(a.cmd)}
                >{a.label}</button>
            ))}
        </div>
    );
}

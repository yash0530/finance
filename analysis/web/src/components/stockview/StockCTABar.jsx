/**
 * CTA bar for ticker actions.
 */
export default function StockCTABar({ ticker, onRunCommand, onRunResearch }) {
    const actions = [
        { label: 'Run thesis', primary: true, onClick: () => onRunResearch?.(ticker) },
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
                    onClick={() => a.onClick ? a.onClick() : onRunCommand(a.cmd)}
                >{a.label}</button>
            ))}
        </div>
    );
}

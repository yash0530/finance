import RefreshButton from './RefreshButton';

export default function PanelShell({ title, subtitle, area, onRefresh, loading, error, children, id }) {
    return (
        <section
            id={id}
            className="glass-card"
            style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%', cursor: 'default' }}
        >
            <header style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: 'var(--spacing-sm)', gap: 8,
            }}>
                <div>
                    <h3 style={{ fontSize: '0.82rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>{title}</h3>
                    {subtitle && <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{subtitle}</div>}
                </div>
                {onRefresh && <RefreshButton onClick={onRefresh} loading={loading} />}
            </header>
            {error && <div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div>}
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto', maxHeight: 360 }}>
                {children}
            </div>
        </section>
    );
}

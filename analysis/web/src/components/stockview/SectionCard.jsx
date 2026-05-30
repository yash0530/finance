export default function SectionCard({ title, children, id, right }) {
    return (
        <section id={id} className="glass-card" style={{ cursor: 'default' }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-sm)' }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 700, margin: 0 }}>{title}</h3>
                {right}
            </header>
            {children}
        </section>
    );
}

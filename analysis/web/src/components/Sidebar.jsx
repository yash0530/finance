import { useRipple } from '../hooks/useRipple';

const NAV_ITEMS = [
    { id: 'market',    label: 'Market' },
    { id: 'stock',     label: 'Stock View' },
    { id: 'research',  label: 'Research' },
    { id: 'terminal',  label: 'Daily Scan' },
    { id: 'console',   label: 'Console' },
    { id: 'library',   label: 'Library' },
    { id: 'screener',  label: 'Screener' },
    { id: 'settings',  label: 'Settings' },
];

export default function Sidebar({ currentPage, onNavigate }) {
    const createRipple = useRipple();

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon" style={{ background: 'var(--accent-blue)', color: '#fff', fontSize: '0.9rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, borderRadius: 8 }}>E</div>
                <div>
                    <div className="sidebar-logo-text">Edge</div>
                    <div className="sidebar-logo-sub">Personal Markets Terminal</div>
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="sidebar-section-label">Workspace</div>
                {NAV_ITEMS.map(item => (
                    <button
                        key={item.id}
                        id={`nav-${item.id}`}
                        className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                        onClick={(e) => { createRipple(e); onNavigate(item.id); }}
                    >
                        <span>{item.label}</span>
                    </button>
                ))}
            </nav>

            <div className="sidebar-bottom">
                <button
                    id="nav-docs"
                    className={`nav-item ${currentPage === 'docs' ? 'active' : ''}`}
                    onClick={(e) => { createRipple(e); onNavigate('docs'); }}
                    title="Documentation"
                    style={{ width: '100%' }}
                >
                    <span>? Docs</span>
                </button>
            </div>
        </aside>
    );
}

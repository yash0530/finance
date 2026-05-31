import { useRipple } from '../hooks/useRipple';

const NAV_ITEMS = [
    { id: 'market',    label: 'Market', short: 'M' },
    { id: 'stock',     label: 'Stock View', short: 'SV' },
    { id: 'research',  label: 'Research', short: 'R' },
    { id: 'terminal',  label: 'Daily Scan', short: 'DS' },
    { id: 'console',   label: 'Console', short: 'C' },
    { id: 'review',    label: 'Review', short: 'RV' },
    { id: 'library',   label: 'Library', short: 'L' },
    { id: 'screener',  label: 'Screener', short: 'SC' },
    { id: 'patterns',  label: 'Patterns', short: 'PT' },
    { id: 'settings',  label: 'Settings', short: 'SE' },
];

export default function Sidebar({ currentPage, onNavigate, collapsed, onToggleCollapsed }) {
    const createRipple = useRipple();

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">E</div>
                <div className="sidebar-brand">
                    <div className="sidebar-logo-text">Edge</div>
                    <div className="sidebar-logo-sub">Research Cockpit</div>
                </div>
                <button
                    id="sidebar-collapse-toggle"
                    type="button"
                    className="sidebar-toggle"
                    onClick={onToggleCollapsed}
                    aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                    aria-pressed={collapsed}
                    title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                    <span />
                    <span />
                    <span />
                </button>
            </div>

            <nav className="sidebar-nav">
                <div className="sidebar-section-label">Workspace</div>
                {NAV_ITEMS.map(item => (
                    <button
                        key={item.id}
                        id={`nav-${item.id}`}
                        className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                        onClick={(e) => { createRipple(e); onNavigate(item.id); }}
                        title={item.label}
                    >
                        <span className="nav-short" aria-hidden="true">{item.short}</span>
                        <span className="nav-label">{item.label}</span>
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
                    <span className="nav-short" aria-hidden="true">?</span>
                    <span className="nav-label">? Docs</span>
                </button>
            </div>
        </aside>
    );
}

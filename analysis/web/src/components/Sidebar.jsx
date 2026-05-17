import { useState } from 'react';

const NAV_ITEMS = [
    { id: 'portfolio',      icon: '💼', label: 'Portfolio',      section: 'main' },
    { id: 'deep-research-v2', icon: '🚀', label: 'Deep Research v2', section: 'main' },
    { id: 'deep-research',  icon: '🧠', label: 'Deep Research',  section: 'main' },
    { id: 'research',       icon: '🔬', label: 'Quick Research', section: 'main' },
    { id: 'history',        icon: '🕰️', label: 'History',        section: 'main' },
    { id: 'watchlist',      icon: '👁️',  label: 'Watchlist',     section: 'main' },
    { id: 'rebalance',      icon: '⚖️',  label: 'Rebalance',     section: 'main' },
    { id: 'alerts',         icon: '🔔', label: 'Alerts',         section: 'main' },
    { id: 'market',         icon: '📊', label: 'S&P 500',        section: 'tools' },
    { id: 'settings',       icon: '⚙️',  label: 'LLM Settings',  section: 'tools' },
];

export default function Sidebar({ currentPage, onNavigate, portfolioConnected }) {
    const mainItems  = NAV_ITEMS.filter(n => n.section === 'main');
    const toolsItems = NAV_ITEMS.filter(n => n.section === 'tools');

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">📈</div>
                <div>
                    <div className="sidebar-logo-text">Portfolio Intel</div>
                    <div className="sidebar-logo-sub">AI Research Platform</div>
                </div>
            </div>

            {/* Nav */}
            <nav className="sidebar-nav">
                <div className="sidebar-section-label">Dashboard</div>
                {mainItems.map(item => (
                    <button
                        key={item.id}
                        id={`nav-${item.id}`}
                        className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        <span>{item.label}</span>
                        {item.id === 'portfolio' && portfolioConnected && (
                            <span style={{
                                marginLeft: 'auto',
                                width: 7, height: 7,
                                borderRadius: '50%',
                                background: 'var(--accent-green)',
                                flexShrink: 0,
                            }} />
                        )}
                    </button>
                ))}

                <div className="sidebar-section-label">Tools</div>
                {toolsItems.map(item => (
                    <button
                        key={item.id}
                        id={`nav-${item.id}`}
                        className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        <span>{item.label}</span>
                    </button>
                ))}
            </nav>

            {/* Bottom status */}
            <div className="sidebar-bottom">
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <span style={{
                            width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                            background: portfolioConnected ? 'var(--accent-green)' : 'var(--text-muted)',
                        }} />
                        {portfolioConnected ? 'Robinhood connected' : 'Not connected'}
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>
                        v2.0 · Portfolio Intel
                    </div>
                </div>
            </div>
        </aside>
    );
}

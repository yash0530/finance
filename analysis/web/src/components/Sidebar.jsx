import { useState } from 'react';
import { useRipple } from '../hooks/useRipple';

const NAV_ITEMS = [
    { id: 'portfolio',      label: 'Portfolio',      section: 'main' },
    { id: 'deep-research',  label: 'Deep Research',  section: 'main' },
    { id: 'history',        label: 'History',        section: 'main' },
    { id: 'market',         label: 'S&P 500',        section: 'tools' },
    { id: 'docs',           label: 'Docs',           section: 'tools' },
    { id: 'settings',       label: 'LLM Settings',  section: 'tools' },
];

export default function Sidebar({ currentPage, onNavigate, portfolioConnected }) {
    const createRipple = useRipple();
    const mainItems  = NAV_ITEMS.filter(n => n.section === 'main');
    const toolsItems = NAV_ITEMS.filter(n => n.section === 'tools');

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon" style={{ background: 'var(--accent-blue)', color: '#fff', fontSize: '0.9rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, borderRadius: 8 }}>PI</div>
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
                        onClick={(e) => { createRipple(e); onNavigate(item.id); }}
                    >
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
                        onClick={(e) => { createRipple(e); onNavigate(item.id); }}
                    >
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
                        Portfolio Intel
                    </div>
                </div>
            </div>
        </aside>
    );
}

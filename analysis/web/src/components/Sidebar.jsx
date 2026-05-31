import { useState } from 'react';
import { useRipple } from '../hooks/useRipple';

const NAV_SECTIONS = [
    {
        section: 'Discover',
        items: [
            { id: 'discover', label: 'Discover', short: 'D' },
        ],
    },
    {
        section: 'Research',
        items: [
            { id: 'stock',    label: 'Stock View', short: 'SV' },
            { id: 'research', label: 'Research', short: 'R' },
            { id: 'console',  label: 'Console', short: 'C' },
        ],
    },
    {
        section: 'Track',
        items: [
            { id: 'library',  label: 'Library', short: 'L' },
            { id: 'review',   label: 'Review', short: 'RV' },
        ],
    },
];

export default function Sidebar({ currentPage, onNavigate, onSelectTicker, onRunResearch, collapsed, onToggleCollapsed }) {
    const createRipple = useRipple();
    const [ticker, setTicker] = useState('');

    const submitTicker = (action) => {
        const t = ticker.trim().toUpperCase();
        if (!t) return;
        if (action === 'research') onRunResearch?.(t);
        else onSelectTicker?.(t);
        setTicker('');
    };

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

            <form
                className="sidebar-ticker-entry"
                onSubmit={(e) => { e.preventDefault(); submitTicker('stock'); }}
            >
                <input
                    id="global-ticker-input"
                    className="sidebar-ticker-input"
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    placeholder="Go to ticker…"
                    aria-label="Go to ticker"
                    autoComplete="off"
                    spellCheck={false}
                />
                <button
                    id="global-ticker-research"
                    type="button"
                    className="sidebar-ticker-go"
                    title="Run Deep Research on this ticker"
                    aria-label="Run Deep Research"
                    disabled={!ticker.trim()}
                    onClick={() => submitTicker('research')}
                >
                    R→
                </button>
            </form>

            <nav className="sidebar-nav">
                {NAV_SECTIONS.map(group => (
                    <div key={group.section} className="sidebar-section">
                        <div className="sidebar-section-label">{group.section}</div>
                        {group.items.map(item => (
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
                    </div>
                ))}
            </nav>

            <div className="sidebar-bottom">
                <button
                    id="nav-settings"
                    className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
                    onClick={(e) => { createRipple(e); onNavigate('settings'); }}
                    title="Settings"
                    style={{ width: '100%' }}
                >
                    <span className="nav-short" aria-hidden="true">SE</span>
                    <span className="nav-label">Settings</span>
                </button>
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

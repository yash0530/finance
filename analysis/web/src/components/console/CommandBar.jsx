import { useState, useEffect, useRef } from 'react';

const HINTS = [
    '/thesis <T>   — full thesis report (~$0.60)',
    '/dossier <T>  — deep dossier (~$2-15)',
    '/why <T>      — quick 3-sentence why (~$0.05)   [Phase 2]',
    '/theme <slug> — theme-level verdict             [Phase 4]',
    '/compare <A> <B> <C> — ranking + head-to-head   [Phase 4]',
];

export default function CommandBar({ value, onChange, onSubmit, disabled }) {
    const [showHints, setShowHints] = useState(false);
    const inputRef = useRef(null);

    useEffect(() => {
        if (value) inputRef.current?.focus();
    }, [value]);

    return (
        <div style={{ position: 'relative' }}>
            <form
                onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
                style={{ display: 'flex', gap: 8, alignItems: 'center' }}
            >
                <input
                    id="console-command-input"
                    ref={inputRef}
                    className="input"
                    placeholder="Type a command, e.g. /thesis NVDA"
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    onFocus={() => setShowHints(true)}
                    onBlur={() => setTimeout(() => setShowHints(false), 150)}
                    disabled={disabled}
                    style={{ fontFamily: 'var(--font-mono, monospace)' }}
                />
                <button id="console-run-btn" className="btn btn-primary" type="submit" disabled={disabled || !value.trim()}>
                    {disabled ? <><span className="spinner spinner-sm" /> Running…</> : 'Run'}
                </button>
            </form>
            {showHints && (
                <div className="glass-card" style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4, zIndex: 20, cursor: 'default' }}>
                    {HINTS.map(h => (
                        <div key={h} style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono, monospace)', padding: '2px 0' }}>{h}</div>
                    ))}
                </div>
            )}
        </div>
    );
}

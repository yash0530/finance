import { useState, useEffect, useRef } from 'react';
import { getThemes, getTerminalWatchlist, getThemeTickers } from '../../utils/api';

const HINTS = [
    '/thesis <T>          — full thesis report (~$0.60)',
    '/dossier <T>         — deep dossier (~$2-15)',
    '/why <T>             — quick 3-sentence why (~$0.05, cached 4h)',
    '/theme <slug>        — theme-level bull/bear/judge verdict',
    '/compare <A> <B> <C> — ranking + head-to-head',
];

export default function CommandBar({ value, onChange, onSubmit, disabled }) {
    const [showHints, setShowHints] = useState(false);
    const [availableThemes, setAvailableThemes] = useState([]);
    const [watchlistTickers, setWatchlistTickers] = useState([]);
    const [tickerSuggestions, setTickerSuggestions] = useState([]);
    const inputRef = useRef(null);

    // Fetch watchlist + themes to build autocomplete index
    useEffect(() => {
        let active = true;
        async function fetchAutocompleteData() {
            try {
                const watchlistRes = await getTerminalWatchlist();
                const themesRes = await getThemes();
                if (!active) return;

                const watchlist = (watchlistRes.items || []).map(item => item.ticker);
                const themes = themesRes.themes || [];

                setWatchlistTickers(watchlist);
                setAvailableThemes(themes);

                const themeTickersSet = new Set();
                // Fetch tickers in parallel for each theme slug
                await Promise.all(
                    themes.map(async (t) => {
                        try {
                            const tRes = await getThemeTickers(t.slug);
                            if (active && tRes.tickers) {
                                tRes.tickers.forEach(tick => {
                                    if (tick.ticker) themeTickersSet.add(tick.ticker);
                                    else if (typeof tick === 'string') themeTickersSet.add(tick);
                                });
                            }
                        } catch (err) {
                            // ignore theme fetch error
                        }
                    })
                );

                if (!active) return;
                const defaultTickers = ["NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM", "MRVL", "SMCI", "DELL", "ORCL", "MSFT"];
                const uniqueTickers = Array.from(new Set([...watchlist, ...themeTickersSet, ...defaultTickers]));
                setTickerSuggestions(uniqueTickers);
            } catch (e) {
                console.error("Failed to build autocomplete index:", e);
            }
        }
        fetchAutocompleteData();
        return () => { active = false; };
    }, []);

    useEffect(() => {
        if (value) inputRef.current?.focus();
    }, [value]);

    // Autocomplete parsing logic
    const parts = value.split(' ');
    const cmd = parts[0].toLowerCase();
    const isThemeCmd = cmd === '/theme';
    const isTickerCmd = ['/thesis', '/dossier', '/why', '/compare'].includes(cmd);

    let filteredSuggestions = [];
    let suggestionType = null; // 'theme' or 'ticker'

    if (isThemeCmd && parts.length > 1) {
        const query = parts.slice(1).join(' ').trim().toLowerCase();
        filteredSuggestions = availableThemes
            .filter(t => t.slug.toLowerCase().includes(query) || t.name.toLowerCase().includes(query))
            .map(t => ({ value: t.slug, label: `${t.slug} — ${t.name}` }));
        suggestionType = 'theme';
    } else if (isTickerCmd && parts.length > 1) {
        const lastPart = parts[parts.length - 1].trim().toUpperCase();
        if (lastPart) {
            filteredSuggestions = tickerSuggestions
                .filter(t => t.startsWith(lastPart))
                .map(t => ({ value: t, label: t }))
                .slice(0, 10); // cap suggestions list size at 10
            suggestionType = 'ticker';
        }
    }

    const handleSelectSuggestion = (s) => {
        if (suggestionType === 'theme') {
            onChange(`/theme ${s.value}`);
        } else if (suggestionType === 'ticker') {
            const newParts = [...parts];
            newParts[newParts.length - 1] = s.value;
            onChange(newParts.join(' ') + ' ');
        }
        // Bring focus back to input
        setTimeout(() => inputRef.current?.focus(), 50);
    };

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
                    onBlur={() => setTimeout(() => setShowHints(false), 200)}
                    disabled={disabled}
                    style={{ fontFamily: 'var(--font-mono, monospace)' }}
                    autoComplete="off"
                />
                <button id="console-run-btn" className="btn btn-primary" type="submit" disabled={disabled || !value.trim()}>
                    {disabled ? <><span className="spinner spinner-sm" /> Running…</> : 'Run'}
                </button>
            </form>

            {showHints && (
                <div className="glass-card" style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4, zIndex: 999,
                    cursor: 'default', padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 6,
                    maxHeight: 220, overflowY: 'auto', border: '1px solid var(--border-color)'
                }}>
                    {filteredSuggestions.length > 0 ? (
                        <>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 2 }}>
                                Suggestions
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {filteredSuggestions.map((s, idx) => (
                                    <div
                                        key={idx}
                                        onMouseDown={(e) => {
                                            e.preventDefault(); // prevent input blur
                                            handleSelectSuggestion(s);
                                        }}
                                        style={{
                                            fontSize: '0.74rem', padding: '6px 8px', borderRadius: 'var(--radius-sm, 4px)',
                                            background: 'rgba(255,255,255,0.02)', border: '1px solid transparent',
                                            cursor: 'pointer', fontFamily: 'var(--font-mono, monospace)', display: 'flex', justifyContent: 'space-between'
                                        }}
                                        className="suggestion-item"
                                    >
                                        <span>{s.label}</span>
                                        <span style={{ color: 'var(--text-muted)', fontSize: '0.66rem' }}>Select &crarr;</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        <>
                            <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 2 }}>
                                Console Command Syntax
                            </div>
                            {HINTS.map(h => (
                                <div key={h} style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono, monospace)', padding: '2px 0' }}>
                                    {h}
                                </div>
                            ))}
                        </>
                    )}
                </div>
            )}
            {/* Style suggestions hover */}
            <style dangerouslySetInnerHTML={{ __html: `
                .suggestion-item:hover {
                    background: rgba(45,126,247,0.12) !important;
                    border-color: rgba(45,126,247,0.3) !important;
                    color: var(--text-primary) !important;
                }
            `}} />
        </div>
    );
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { streamDeepResearch } from '../utils/api';
import CommandBar from '../components/console/CommandBar';
import StreamView from '../components/console/StreamView';
import RunHistoryRail from '../components/console/RunHistoryRail';

const BUDGET_BY_COMMAND = { '/thesis': 'normal', '/dossier': 'deep' };

function parseCommand(raw) {
    const parts = raw.trim().split(/\s+/);
    const cmd = (parts[0] || '').toLowerCase();
    const args = parts.slice(1);
    return { cmd, args };
}

const EMPTY_RUN = {
    sectorInfo: null,
    toolCalls: [],
    debateTurns: {},
    verdict: null,
    error: null,
    complete: null,
};

/**
 * Console — slash-command bar + SSE stream + run-history rail.
 *
 * Phase 1 supports /thesis <T> and /dossier <T>, dispatched to the existing
 * v2 deep-research stream. Phase 4 replaces this with the console_orchestrator
 * endpoint and the full command set (/why, /theme, /compare).
 */
export default function ConsolePage({ initialCommand, onCommandConsumed }) {
    const [command, setCommand] = useState('');
    const [running, setRunning] = useState(false);
    const [run, setRun] = useState(null);
    const [history, setHistory] = useState([]);
    const closeRef = useRef(null);

    const start = useCallback((raw) => {
        const { cmd, args } = parseCommand(raw);
        const budget = BUDGET_BY_COMMAND[cmd];
        if (!budget) {
            setRun({ ...EMPTY_RUN, error: `Command "${cmd}" not available yet. Try /thesis <T> or /dossier <T>.` });
            return;
        }
        const ticker = (args[0] || '').toUpperCase();
        if (!ticker) {
            setRun({ ...EMPTY_RUN, error: `Usage: ${cmd} <TICKER>` });
            return;
        }

        setRunning(true);
        setRun({ ...EMPTY_RUN });
        setHistory(prev => [{ command: raw.trim(), status: 'running' }, ...prev].slice(0, 20));

        const finish = (status) => {
            setHistory(prev => prev.map((h, i) => (i === 0 ? { ...h, status } : h)));
        };

        const close = streamDeepResearch(ticker, {
            onContextLoaded: (d) => setRun(r => ({ ...r, sectorInfo: d })),
            onToolCallComplete: (d) => setRun(r => ({ ...r, toolCalls: [...r.toolCalls, d] })),
            onToolCallError: (d) => setRun(r => ({ ...r, toolCalls: [...r.toolCalls, { ...d, error: d.error }] })),
            onDebateTurn: (d) => setRun(r => ({ ...r, debateTurns: { ...r.debateTurns, [d.agent]: d.output } })),
            onDebateComplete: (d) => setRun(r => ({ ...r, verdict: d.verdict })),
            onReportComplete: (d) => { setRun(r => ({ ...r, complete: d })); setRunning(false); finish('done'); },
            onError: (d) => { setRun(r => ({ ...r, error: d.error || 'stream error' })); setRunning(false); finish('error'); },
        }, { budget });
        closeRef.current = close;
    }, []);

    // Consume a deep-linked command from Stock View (e.g. "/thesis NVDA").
    useEffect(() => {
        if (initialCommand) {
            setCommand(initialCommand);
            start(initialCommand);
            onCommandConsumed?.();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialCommand]);

    const cancel = useCallback(() => {
        closeRef.current?.();
        setRunning(false);
    }, []);

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Console</h1>
                    <p className="page-subtitle">Slash commands · live SSE stream · on-demand reasoning</p>
                </div>
                {running && <button className="btn btn-danger" onClick={cancel}>Stop</button>}
            </div>

            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
                <CommandBar
                    value={command}
                    onChange={setCommand}
                    onSubmit={() => start(command)}
                    disabled={running}
                />
            </div>

            <div style={{ display: 'flex', gap: 'var(--spacing-lg)', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                    {run ? <StreamView run={run} /> : (
                        <div className="glass-card" style={{ cursor: 'default' }}>
                            <div className="empty-state">
                                <h3 style={{ color: 'var(--text-secondary)' }}>Analysis Console</h3>
                                <p style={{ fontSize: '0.825rem', maxWidth: 460, lineHeight: 1.7 }}>
                                    Run on-demand analysis with slash commands. Start with
                                    {' '}<code>/thesis NVDA</code> for a full report or
                                    {' '}<code>/dossier NVDA</code> for a deep dive.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
                <RunHistoryRail history={history} onReplay={(c) => { setCommand(c); start(c); }} />
            </div>
        </div>
    );
}

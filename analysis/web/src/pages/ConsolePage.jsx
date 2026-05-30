import { useState, useEffect, useRef, useCallback } from 'react';
import { streamConsole } from '../utils/api';
import CommandBar from '../components/console/CommandBar';
import StreamView from '../components/console/StreamView';
import RunHistoryRail from '../components/console/RunHistoryRail';

const EMPTY_RUN = {
    sectorInfo: null,
    pipeline: null,
    agentPlans: [],
    activeTools: [],
    toolCalls: [],
    debateTurns: {},
    verdict: null,
    selfCritique: null,
    memoDelta: null,
    quickTake: null,
    themeInfo: null,
    compare: { candidates: [], ranking: null },
    budgetWarnings: [],
    error: null,
    complete: null,
};

/**
 * Console — slash-command bar + SSE stream + run-history rail.
 *
 * Dispatches every command (/thesis, /dossier, /why, /theme, /compare) to the
 * console_orchestrator endpoint and renders the unified event stream.
 */
export default function ConsolePage({ initialCommand, onCommandConsumed }) {
    const [command, setCommand] = useState('');
    const [running, setRunning] = useState(false);
    const [run, setRun] = useState(null);
    const [history, setHistory] = useState([]);
    const abortRef = useRef(null);

    const start = useCallback((raw) => {
        const cmd = (raw || '').trim();
        if (!cmd) return;

        setRunning(true);
        setRun({ ...EMPTY_RUN, compare: { candidates: [], ranking: null }, toolCalls: [], debateTurns: {} });
        setHistory(prev => [{ command: cmd, status: 'running' }, ...prev].slice(0, 20));
        const finish = (status) => setHistory(prev => prev.map((h, i) => (i === 0 ? { ...h, status } : h)));

        const onEvent = (ev, d) => {
            setRun(r => {
                const next = { ...r };
                switch (ev) {
                    case 'pipeline_start': next.pipeline = d; break;
                    case 'context_loaded': next.sectorInfo = d; break;
                    case 'agent_plan': next.agentPlans = [...(r.agentPlans || []), d]; break;
                    case 'tool_call_start':
                        next.activeTools = [...(r.activeTools || []), d];
                        break;
                    case 'tool_call_complete':
                        next.toolCalls = [...r.toolCalls, d];
                        next.activeTools = (r.activeTools || []).filter((t, i) => !(t.tool === d.tool && i === (r.activeTools || []).findIndex(x => x.tool === d.tool)));
                        break;
                    case 'tool_call_error':
                        next.toolCalls = [...r.toolCalls, { ...d, error: d.error }];
                        next.activeTools = (r.activeTools || []).filter((t, i) => !(t.tool === d.tool && i === (r.activeTools || []).findIndex(x => x.tool === d.tool)));
                        break;
                    case 'debate_turn': next.debateTurns = { ...r.debateTurns, [d.agent]: d.output }; break;
                    case 'debate_complete': next.verdict = d.verdict; break;
                    case 'self_critique_start': next.selfCritique = { running: true }; break;
                    case 'self_critique': next.selfCritique = { ...d, running: false }; break;
                    case 'memo_delta_proposed': next.memoDelta = d; break;
                    case 'budget_warning': next.budgetWarnings = [...(r.budgetWarnings || []), d]; break;
                    case 'quick_take': next.quickTake = d; break;
                    case 'theme_start': next.themeInfo = d; break;
                    case 'compare_start': next.compare = { candidates: [], ranking: null }; break;
                    case 'compare_candidate':
                        next.compare = { ...r.compare, candidates: [...r.compare.candidates, d] }; break;
                    case 'compare_ranking':
                        next.compare = { ...r.compare, ranking: d }; break;
                    case 'report_complete':
                    case 'console_complete': next.complete = d; break;
                    case 'console_error':
                    case 'error': next.error = d.error || 'stream error'; break;
                    default: break;
                }
                return next;
            });
            if (ev === 'report_complete' || ev === 'console_complete') { setRunning(false); finish('done'); }
            if (ev === 'console_error' || ev === 'error') { setRunning(false); finish('error'); }
        };

        abortRef.current = streamConsole(
            cmd,
            onEvent,
            (errMsg) => { setRun(r => ({ ...r, error: errMsg })); setRunning(false); finish('error'); },
            () => { setRunning(false); finish(prev => prev); },
        );
    }, []);

    useEffect(() => {
        if (initialCommand) {
            setCommand(initialCommand);
            start(initialCommand);
            onCommandConsumed?.();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialCommand]);

    const cancel = useCallback(() => {
        abortRef.current?.();
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
                <CommandBar value={command} onChange={setCommand} onSubmit={() => start(command)} disabled={running} />
            </div>

            <div style={{ display: 'flex', gap: 'var(--spacing-lg)', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                    {run ? <StreamView run={run} /> : (
                        <div className="glass-card" style={{ cursor: 'default' }}>
                            <div className="empty-state">
                                <h3 style={{ color: 'var(--text-secondary)' }}>Analysis Console</h3>
                                <p style={{ fontSize: '0.825rem', maxWidth: 480, lineHeight: 1.7 }}>
                                    Run on-demand analysis with slash commands:
                                    {' '}<code>/thesis NVDA</code>, <code>/dossier NVDA</code>,
                                    {' '}<code>/why NVDA</code>, <code>/theme ai-infra</code>,
                                    {' '}<code>/compare NVDA AMD AVGO</code>.
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

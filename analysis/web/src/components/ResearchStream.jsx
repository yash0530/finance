import { useState, useCallback, useRef, useEffect } from 'react';
import { streamQuickResearch } from '../utils/api';

// ── Stage metadata ────────────────────────────────────────
const STAGE_META = {
    fundamentals:     { icon: '📊', label: 'Fundamentals',       desc: 'Revenue, margins, valuation ratios' },
    financial_trends: { icon: '📈', label: 'Financial Trends',   desc: 'Quarterly trajectory analysis (8-12 quarters)' },
    valuation:        { icon: '⚖️', label: 'Valuation & DCF',     desc: 'Intrinsic value modeling & peer comparison' },
    technicals:       { icon: '🔧', label: 'Technical Analysis', desc: 'RSI, MACD, Bollinger, chart patterns' },
    risk_management:  { icon: '🛡️', label: 'Risk & Sizing',       desc: 'Kelly Criterion & volatility scaling' },
    sentiment:        { icon: '🌡️', label: 'Market Sentiment',  desc: 'News, analyst ratings, Reddit signals' },
    edgar:            { icon: '📄', label: 'SEC Filings',        desc: '10-K/10-Q key sections & AI summary' },
    thesis:           { icon: '🤖', label: 'AI Thesis',          desc: 'Investment thesis with bull/bear case' },
};

// ── Custom hook: useResearchStream ────────────────────────
export function useResearchStream() {
    const [stages, setStages]       = useState({});
    const [stageOrder, setOrder]    = useState([]);
    const [report, setReport]       = useState(null);
    const [isStreaming, setStream]   = useState(false);
    const [error, setError]         = useState('');
    const [pipelineInfo, setPipeline] = useState(null);
    const cleanupRef = useRef(null);

    const startResearch = useCallback((ticker, options = {}) => {
        // Clean up previous stream
        cleanupRef.current?.();
        setStages({});
        setOrder([]);
        setReport(null);
        setError('');
        setStream(true);
        setPipeline(null);

        const cleanup = streamQuickResearch(ticker, {
            onPipelineStart(data) {
                setPipeline(data);
                setOrder(data.stages || []);
                // Initialize all stages as pending
                const initial = {};
                (data.stages || []).forEach(s => {
                    initial[s] = { status: 'pending', data: null, error: null, message: '' };
                });
                setStages(initial);
            },

            onStageStart(data) {
                setStages(prev => ({
                    ...prev,
                    [data.stage]: {
                        ...prev[data.stage],
                        status: 'running',
                        message: data.message || '',
                    }
                }));
            },

            onStageComplete(data) {
                setStages(prev => ({
                    ...prev,
                    [data.stage]: {
                        ...prev[data.stage],
                        status: 'complete',
                        data: data.data,
                    }
                }));
            },

            onStageError(data) {
                setStages(prev => ({
                    ...prev,
                    [data.stage]: {
                        ...prev[data.stage],
                        status: 'error',
                        error: data.error,
                    }
                }));
            },

            onReportComplete(data) {
                setReport(data);
                setStream(false);
            },

            onError(data) {
                setError(data.error || 'Connection lost');
                setStream(false);
            },
        }, options);

        cleanupRef.current = cleanup;
    }, []);

    const cancel = useCallback(() => {
        cleanupRef.current?.();
        setStream(false);
    }, []);

    // Cleanup on unmount
    useEffect(() => () => cleanupRef.current?.(), []);

    return {
        stages,
        stageOrder,
        report,
        isStreaming,
        error,
        pipelineInfo,
        startResearch,
        cancel,
    };
}


// ── Research Timeline Component ───────────────────────────
export function ResearchTimeline({ stages, stageOrder }) {
    const completedCount = stageOrder.filter(s => stages[s]?.status === 'complete' || stages[s]?.status === 'error').length;
    const progressPct = stageOrder.length > 0 ? (completedCount / stageOrder.length) * 100 : 0;

    return (
        <div className="research-timeline">
            {/* Progress bar */}
            <div className="research-progress-track">
                <div
                    className="research-progress-fill"
                    style={{ width: `${progressPct}%` }}
                />
            </div>

            {/* Stage list */}
            <div className="research-stages">
                {stageOrder.map((stageKey, i) => {
                    const stage = stages[stageKey] || { status: 'pending' };
                    const meta = STAGE_META[stageKey] || { icon: '⏳', label: stageKey, desc: '' };

                    return (
                        <div
                            key={stageKey}
                            className={`research-stage-item research-stage-${stage.status}`}
                        >
                            <div className="research-stage-indicator">
                                {stage.status === 'running' ? (
                                    <span className="spinner spinner-sm" />
                                ) : stage.status === 'complete' ? (
                                    <span className="research-stage-check">✓</span>
                                ) : stage.status === 'error' ? (
                                    <span className="research-stage-error-icon">!</span>
                                ) : (
                                    <span className="research-stage-dot" />
                                )}
                            </div>
                            <div className="research-stage-content">
                                <div className="research-stage-header">
                                    <span className="research-stage-icon">{meta.icon}</span>
                                    <span className="research-stage-label">{meta.label}</span>
                                    {stage.status === 'running' && (
                                        <span className="research-stage-running-text pulse">
                                            {stage.message || 'Processing...'}
                                        </span>
                                    )}
                                    {stage.status === 'error' && (
                                        <span className="badge badge-red" style={{ fontSize: '0.65rem' }}>
                                            Failed — continuing
                                        </span>
                                    )}
                                </div>
                                {stage.status === 'pending' && (
                                    <div className="research-stage-desc">{meta.desc}</div>
                                )}
                            </div>
                            {/* Connector line */}
                            {i < stageOrder.length - 1 && (
                                <div className={`research-stage-connector ${
                                    stage.status === 'complete' || stage.status === 'error' ? 'filled' : ''
                                }`} />
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

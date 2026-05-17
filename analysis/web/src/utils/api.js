/**
 * api.js — Unified API client for all backend endpoints.
 * Extends the existing S&P 500 calls with portfolio, research, settings, watchlist, alerts.
 */

const API_BASE = 'http://localhost:5001/api';

// ──────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
}

// ──────────────────────────────────────────────────────────
// Existing S&P 500 Endpoints (unchanged)
// ──────────────────────────────────────────────────────────

export const fetchCompanies = (sortBy = 'forward_pe', order = 'asc') =>
    apiFetch(`${API_BASE}/companies?sort_by=${sortBy}&order=${order}`);

export const fetchSectors = () => apiFetch(`${API_BASE}/sectors`);

export const fetchCompaniesBySector = (sector) =>
    apiFetch(`${API_BASE}/companies/${encodeURIComponent(sector)}`);

export const fetchStats = () => apiFetch(`${API_BASE}/stats`);

export const searchCompanies = (query) =>
    apiFetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);

export const fetchCompanyByTicker = (ticker) =>
    apiFetch(`${API_BASE}/company/${encodeURIComponent(ticker)}`);

export const refreshData = () =>
    apiFetch(`${API_BASE}/refresh`, { method: 'POST' });

export const healthCheck = () => apiFetch(`${API_BASE}/health`);

export const getVersion = () => apiFetch(`${API_BASE}/version`);

export const fetchStockHistory = (ticker, refresh = false) =>
    apiFetch(`${API_BASE}/company/${encodeURIComponent(ticker)}/history${refresh ? '?refresh=true' : ''}`);

export const fetchFinancials = (ticker, refresh = false) =>
    apiFetch(`${API_BASE}/company/${encodeURIComponent(ticker)}/financials${refresh ? '?refresh=true' : ''}`);

export const fetchSpotlight = () => apiFetch(`${API_BASE}/spotlight`);

export const fetchHeadShouldersPatterns = () =>
    apiFetch(`${API_BASE}/patterns/head-shoulders`);

export const fetchHeadShouldersForTicker = (ticker) =>
    apiFetch(`${API_BASE}/patterns/head-shoulders/${encodeURIComponent(ticker)}`);

export async function fetchAllPatternsForTicker(ticker) {
    const patternTypes = [
        'head-shoulders', 'inverse-head-shoulders', 'double-top', 'double-bottom',
        'triple-top', 'triple-bottom', 'ascending-triangle', 'descending-triangle',
        'cup-and-handle', 'bullish-flag', 'falling-wedge',
    ];
    const results = await Promise.all(
        patternTypes.map(async (type) => {
            try {
                const data = await apiFetch(`${API_BASE}/patterns/${type}/${encodeURIComponent(ticker)}`);
                return data.detected ? data : null;
            } catch { return null; }
        })
    );
    return results.filter(Boolean).sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
}

// ──────────────────────────────────────────────────────────
// Portfolio
// ──────────────────────────────────────────────────────────

export const getPortfolioStatus = () => apiFetch(`${API_BASE}/portfolio/status`);

export const connectRobinhood = (username, password, otp) =>
    apiFetch(`${API_BASE}/portfolio/connect`, {
        method: 'POST',
        body: JSON.stringify({ username, password, otp }),
    });

export const disconnectRobinhood = () =>
    apiFetch(`${API_BASE}/portfolio/disconnect`, { method: 'POST' });

export const syncPortfolio = () =>
    apiFetch(`${API_BASE}/portfolio/sync`, { method: 'POST' });

export const importPortfolioCSV = (csv) =>
    apiFetch(`${API_BASE}/portfolio/import`, {
        method: 'POST',
        body: JSON.stringify({ csv }),
    });

export const getPortfolioHoldings = () => apiFetch(`${API_BASE}/portfolio/holdings`);
export const getPortfolioSummary = () => apiFetch(`${API_BASE}/portfolio/summary`);

export const getRebalanceAnalysis = (profile = 'moderate') =>
    apiFetch(`${API_BASE}/portfolio/rebalance?profile=${encodeURIComponent(profile)}`);

// ──────────────────────────────────────────────────────────
// Advisor (digest + calibration)
// ──────────────────────────────────────────────────────────

export const getAdvisorDigest = (days = 7) =>
    apiFetch(`${API_BASE}/advisor/digest?days=${days}`);

export const runAdvisorDigest = () =>
    apiFetch(`${API_BASE}/advisor/run-digest`, { method: 'POST' });

export const getCalibration = (backfill = false) =>
    apiFetch(`${API_BASE}/advisor/calibration${backfill ? '?backfill=1' : ''}`);

// ──────────────────────────────────────────────────────────
// Docs (in-app guides)
// ──────────────────────────────────────────────────────────

export const listDocs = () => apiFetch(`${API_BASE}/docs`);

export const getDoc = (slug) =>
    apiFetch(`${API_BASE}/docs/${encodeURIComponent(slug)}`);

// ──────────────────────────────────────────────────────────
// Research
// ──────────────────────────────────────────────────────────

export const getResearchReport = (ticker, { refresh = false, noEdgar = false } = {}) => {
    const params = new URLSearchParams();
    if (refresh) params.set('refresh', 'true');
    if (noEdgar) params.set('no_edgar', 'true');
    const qs = params.toString();
    return apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}${qs ? '?' + qs : ''}`);
};

export const getTicker = (ticker) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/thesis`);

export const compareTickers = (tickers) =>
    apiFetch(`${API_BASE}/research/compare`, {
        method: 'POST',
        body: JSON.stringify({ tickers }),
    });

export const getSectorResearch = (sector) =>
    apiFetch(`${API_BASE}/research/sector/${encodeURIComponent(sector)}`);

/**
 * Open an SSE stream for deep research on a ticker.
 *
 * @param {string} ticker - Stock symbol
 * @param {object} callbacks - Event handlers
 * @param {function} callbacks.onPipelineStart - Called when pipeline begins
 * @param {function} callbacks.onStageStart - Called when a stage begins
 * @param {function} callbacks.onStageComplete - Called when a stage finishes with data
 * @param {function} callbacks.onStageError - Called when a stage fails (non-fatal)
 * @param {function} callbacks.onReportComplete - Called when full report is assembled
 * @param {function} callbacks.onError - Called on connection error
 * @param {object} options - { noEdgar: boolean }
 * @returns {function} cleanup - Call to close the connection
 */
export function streamDeepResearch(ticker, callbacks, options = {}) {
    const params = new URLSearchParams();
    if (options.noEdgar) params.set('no_edgar', 'true');
    const qs = params.toString();
    const url = `${API_BASE}/research/${encodeURIComponent(ticker)}/stream${qs ? '?' + qs : ''}`;

    const eventSource = new EventSource(url);
    let eventsReceived = 0;
    let completedCleanly = false;

    const bump = (handler) => (e) => {
        eventsReceived += 1;
        handler(e);
    };

    eventSource.addEventListener('pipeline_start', bump((e) => {
        callbacks.onPipelineStart?.(JSON.parse(e.data));
    }));

    eventSource.addEventListener('stage_start', bump((e) => {
        callbacks.onStageStart?.(JSON.parse(e.data));
    }));

    eventSource.addEventListener('stage_complete', bump((e) => {
        callbacks.onStageComplete?.(JSON.parse(e.data));
    }));

    eventSource.addEventListener('stage_error', bump((e) => {
        callbacks.onStageError?.(JSON.parse(e.data));
    }));

    eventSource.addEventListener('report_complete', bump((e) => {
        callbacks.onReportComplete?.(JSON.parse(e.data));
        completedCleanly = true;
        eventSource.close();
    }));

    eventSource.onerror = () => {
        // EventSource auto-reconnects on transient errors; only surface terminal CLOSED.
        if (eventSource.readyState !== EventSource.CLOSED) return;
        if (completedCleanly) return;
        const msg = eventsReceived === 0
            ? `Backend rejected the stream (route missing, CORS, or backend down). Tried ${url}`
            : `Stream ended unexpectedly after ${eventsReceived} event(s) without completing`;
        callbacks.onError?.({ error: msg, eventsReceived });
    };

    // Return cleanup function
    return () => {
        eventSource.close();
    };
}

export const getResearchHistory = (ticker, limit = 10) =>
    apiFetch(`${API_BASE}/research/reports/${encodeURIComponent(ticker)}?limit=${limit}`);

// ──────────────────────────────────────────────────────────
// v2 "Living Analyst" — agentic loop + Memo + Calibration
// ──────────────────────────────────────────────────────────

/**
 * Open the v2 SSE stream (agentic loop with multi-agent debate).
 * Event taxonomy (see analysis/docs/next_gen_tool.md §20):
 *   pipeline_start, context_loaded, agent_plan,
 *   tool_call_start, tool_call_complete, tool_call_error,
 *   debate_start, debate_turn, debate_complete,
 *   self_critique_start, self_critique,
 *   memo_delta_proposed, budget_warning, report_complete
 */
export function streamDeepResearchV2(ticker, callbacks, options = {}) {
    const params = new URLSearchParams();
    if (options.budget) params.set('budget', options.budget);
    if (options.refresh) params.set('refresh', 'true');
    const qs = params.toString();
    const url = `${API_BASE}/research/${encodeURIComponent(ticker)}/v2/stream${qs ? '?' + qs : ''}`;

    const es = new EventSource(url);
    let eventsReceived = 0;
    let completedCleanly = false;

    const EVENTS = [
        'pipeline_start', 'context_loaded', 'agent_plan',
        'tool_call_start', 'tool_call_complete', 'tool_call_error',
        'debate_start', 'debate_turn', 'debate_complete',
        'self_critique_start', 'self_critique',
        'memo_delta_proposed', 'budget_warning', 'report_complete',
    ];

    for (const ev of EVENTS) {
        const fn = callbacks['on' + ev.replace(/(^|_)(\w)/g, (_, __, c) => c.toUpperCase())];
        es.addEventListener(ev, (e) => {
            eventsReceived += 1;
            try {
                fn?.(JSON.parse(e.data));
            } catch (err) {
                console.error(`v2 SSE handler for ${ev} failed:`, err);
            }
            if (ev === 'report_complete') {
                completedCleanly = true;
                es.close();
            }
        });
    }

    es.onerror = () => {
        // Only treat CLOSED as terminal — EventSource auto-reconnects on transient drops.
        if (es.readyState !== EventSource.CLOSED) return;
        if (completedCleanly) return;
        const msg = eventsReceived === 0
            ? `Backend rejected the stream (route missing, CORS, or backend down). Tried ${url}`
            : `Stream ended unexpectedly after ${eventsReceived} event(s) without reaching report_complete`;
        callbacks.onError?.({ error: msg, eventsReceived });
    };

    return () => es.close();
}

// Memo
export const getMemo = (ticker) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/memo`);

export const updateMemo = (ticker, content_json, delta_summary = 'manual edit') =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/memo`, {
        method: 'PUT',
        body: JSON.stringify({ content_json, delta_summary }),
    });

export const getMemoHistory = (ticker, limit = 20) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/memo/history?limit=${limit}`);

export const getMemoVersion = (ticker, version) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/memo/version/${version}`);

// Tool-call audit log
export const getToolLog = (ticker, reportId) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/tool-log/${reportId}`);

// Calibration
export const getTickerCalibration = (ticker) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/calibration`);

export const getCalibrationDashboard = () =>
    apiFetch(`${API_BASE}/calibration/dashboard`);

// Sector
export const classifySector = (ticker) =>
    apiFetch(`${API_BASE}/sectors/classify/${encodeURIComponent(ticker)}`);

export const overrideSector = (ticker, sector_key, gics_industry = '') =>
    apiFetch(`${API_BASE}/sectors/classify/${encodeURIComponent(ticker)}`, {
        method: 'POST',
        body: JSON.stringify({ sector_key, gics_industry }),
    });

// Catalysts
export const getCatalysts = (tickers = [], daysAhead = 90) => {
    const qs = new URLSearchParams();
    if (tickers.length) qs.set('tickers', tickers.join(','));
    qs.set('days_ahead', String(daysAhead));
    return apiFetch(`${API_BASE}/catalysts?${qs}`);
};

// Monitoring
export const toggleMonitor = (ticker, enabled = true) =>
    apiFetch(`${API_BASE}/research/${encodeURIComponent(ticker)}/monitor`, {
        method: 'POST',
        body: JSON.stringify({ enabled }),
    });

export const getMonitoringStatus = () =>
    apiFetch(`${API_BASE}/monitoring/status`);

export const getAllResearchHistory = (limit = 50) =>
    apiFetch(`${API_BASE}/research/reports?limit=${limit}`);

export const getResearchReportById = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}`);

export const getResearchReportDrift = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}/drift`);


// ──────────────────────────────────────────────────────────
// LLM Settings
// ──────────────────────────────────────────────────────────

export const getLLMSettings = () => apiFetch(`${API_BASE}/settings/llm`);

export const saveLLMSettings = (settings) =>
    apiFetch(`${API_BASE}/settings/llm`, {
        method: 'POST',
        body: JSON.stringify(settings),
    });

export const testLLMConnection = () =>
    apiFetch(`${API_BASE}/settings/llm/test`, { method: 'POST' });

// ──────────────────────────────────────────────────────────
// Watchlist
// ──────────────────────────────────────────────────────────

export const getWatchlist = () => apiFetch(`${API_BASE}/watchlist`);

export const addToWatchlist = (ticker, notes = '') =>
    apiFetch(`${API_BASE}/watchlist`, {
        method: 'POST',
        body: JSON.stringify({ ticker, notes }),
    });

export const removeFromWatchlist = (ticker) =>
    apiFetch(`${API_BASE}/watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' });

// ──────────────────────────────────────────────────────────
// Alerts
// ──────────────────────────────────────────────────────────

export const getAlerts = (activeOnly = true) =>
    apiFetch(`${API_BASE}/alerts?active_only=${activeOnly}`);

export const createAlert = (ticker, condition, threshold) =>
    apiFetch(`${API_BASE}/alerts`, {
        method: 'POST',
        body: JSON.stringify({ ticker, condition, threshold }),
    });

export const deleteAlert = (alertId) =>
    apiFetch(`${API_BASE}/alerts/${alertId}`, { method: 'DELETE' });

// ──────────────────────────────────────────────────────────
// Formatting & Color Helpers
// ──────────────────────────────────────────────────────────

export const SECTOR_COLORS = {
    'Information Technology': '#2d7ef7',
    'Health Care': '#10d9a0',
    'Financials': '#f59e0b',
    'Consumer Discretionary': '#ec4899',
    'Industrials': '#7c3aed',
    'Consumer Staples': '#06d6f0',
    'Energy': '#f43f5e',
    'Utilities': '#14b8a6',
    'Real Estate': '#6366f1',
    'Materials': '#f97316',
    'Communication Services': '#a855f7',
};

export const getSectorColor = (sector) => SECTOR_COLORS[sector] || '#6b7280';

export const formatCurrency = (value) => {
    if (value == null) return 'N/A';
    if (Math.abs(value) >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (Math.abs(value) >= 1e9)  return `$${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6)  return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
};

export const formatPercent = (value, alreadyPct = false) => {
    if (value == null) return 'N/A';
    const num = alreadyPct ? value : value * 100;
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
};

export const formatNumber = (value, decimals = 2) => {
    if (value == null) return 'N/A';
    return Number(value).toFixed(decimals);
};

export const pnlClass = (value) => {
    if (value == null) return '';
    return value >= 0 ? 'pnl-positive' : 'pnl-negative';
};

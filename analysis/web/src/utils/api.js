/**
 * api.js — Unified API client for all backend endpoints.
 * Extends the existing S&P 500 calls with portfolio, research, settings, watchlist.
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

export const healthCheck = () => apiFetch(`${API_BASE}/health`);

export const getVersion = () => apiFetch(`${API_BASE}/version`);


// ──────────────────────────────────────────────────────────
// Docs (in-app guides)
// ──────────────────────────────────────────────────────────

export const listDocs = () => apiFetch(`${API_BASE}/docs`);

export const getDoc = (slug) =>
    apiFetch(`${API_BASE}/docs/${encodeURIComponent(slug)}`);

// ──────────────────────────────────────────────────────────
// Research
// ──────────────────────────────────────────────────────────

export const getResearchHistory = (ticker, limit = 10) =>
    apiFetch(`${API_BASE}/research/reports/${encodeURIComponent(ticker)}?limit=${limit}`);

// ──────────────────────────────────────────────────────────
// Deep Research — agentic loop + Memo + Calibration
// ──────────────────────────────────────────────────────────

/**
 * Open the deep research SSE stream (agentic loop with multi-agent debate).
 * Event taxonomy (see analysis/docs/next_gen_tool.md §20):
 *   pipeline_start, context_loaded, agent_plan,
 *   tool_call_start, tool_call_complete, tool_call_error,
 *   debate_start, debate_turn, debate_complete,
 *   self_critique_start, self_critique,
 *   memo_delta_proposed, budget_warning, report_complete
 */
export function streamDeepResearch(ticker, callbacks, options = {}) {
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
                console.error(`Deep research SSE handler for ${ev} failed:`, err);
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



export const getAllResearchHistory = (limit = 50) =>
    apiFetch(`${API_BASE}/research/reports?limit=${limit}`);

export const getResearchReportById = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}`);

export const deleteResearchReport = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}`, {
        method: 'DELETE',
    });

export const deleteResearchReportsBulk = (reportIds) =>
    apiFetch(`${API_BASE}/research/reports/delete-bulk`, {
        method: 'POST',
        body: JSON.stringify({ report_ids: reportIds }),
    });

export const getResearchReportDrift = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}/drift`);


// ──────────────────────────────────────────────────────────
// Terminal (daily scan) + Chart
// ──────────────────────────────────────────────────────────

export const getMovers = (universe = 'themes', topN = 10) =>
    apiFetch(`${API_BASE}/terminal/movers?universe=${encodeURIComponent(universe)}&top_n=${topN}`);

export const getTerminalNews = (theme = 'all', limit = 50) =>
    apiFetch(`${API_BASE}/terminal/news?theme=${encodeURIComponent(theme)}&limit=${limit}`);

export const getTerminalWatchlist = () => apiFetch(`${API_BASE}/terminal/watchlist`);

export const addWatchlistTicker = (ticker, notes = '') =>
    apiFetch(`${API_BASE}/terminal/watchlist`, {
        method: 'POST',
        body: JSON.stringify({ ticker, notes }),
    });

export const removeWatchlistTicker = (ticker) =>
    apiFetch(`${API_BASE}/terminal/watchlist/${encodeURIComponent(ticker)}`, {
        method: 'DELETE',
    });

export const getChart = (ticker, range = '1y', interval = '') => {
    const qs = new URLSearchParams({ range });
    if (interval) qs.set('interval', interval);
    return apiFetch(`${API_BASE}/chart/${encodeURIComponent(ticker)}?${qs}`);
};

export const getThemeHeat = () => apiFetch(`${API_BASE}/terminal/theme-heat`);

export const getTerminalCatalysts = (days = 7) =>
    apiFetch(`${API_BASE}/terminal/catalysts?days=${days}`);

export const getFlow = (ticker = '') =>
    apiFetch(`${API_BASE}/terminal/flow${ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''}`);

export const generateHypothesis = (ticker, refresh = false) =>
    apiFetch(`${API_BASE}/terminal/hypothesis`, {
        method: 'POST',
        body: JSON.stringify({ ticker, refresh }),
    });

// ──────────────────────────────────────────────────────────
// Themes
// ──────────────────────────────────────────────────────────

export const getThemes = () => apiFetch(`${API_BASE}/themes`);

export const createTheme = (slug, name, description = '', tickers = []) =>
    apiFetch(`${API_BASE}/themes`, {
        method: 'POST',
        body: JSON.stringify({ slug, name, description, tickers }),
    });

export const deleteTheme = (slug) =>
    apiFetch(`${API_BASE}/themes/${encodeURIComponent(slug)}`, { method: 'DELETE' });

export const getThemeTickers = (slug) =>
    apiFetch(`${API_BASE}/themes/${encodeURIComponent(slug)}/tickers`);

export const addThemeTicker = (slug, ticker, weightHint = 1.0) =>
    apiFetch(`${API_BASE}/themes/${encodeURIComponent(slug)}/tickers`, {
        method: 'POST',
        body: JSON.stringify({ ticker, weight_hint: weightHint }),
    });

export const removeThemeTicker = (slug, ticker) =>
    apiFetch(`${API_BASE}/themes/${encodeURIComponent(slug)}/tickers/${encodeURIComponent(ticker)}`, {
        method: 'DELETE',
    });

export const getThemesByTicker = (ticker) =>
    apiFetch(`${API_BASE}/themes/by-ticker/${encodeURIComponent(ticker)}`);

// ──────────────────────────────────────────────────────────
// Stock View sections (lazy-fetched in parallel)
// ──────────────────────────────────────────────────────────

export const getStockHeader = (ticker) =>
    apiFetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/header`);

export const getStockFundamentals = (ticker) =>
    apiFetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/fundamentals`);

export const getStockTechnicals = (ticker) =>
    apiFetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/technicals`);

export const getStockOwnership = (ticker) =>
    apiFetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/ownership`);

export const getStockFilings = (ticker) =>
    apiFetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/filings`);

// ──────────────────────────────────────────────────────────
// Console (slash-command SSE over POST) + Library memos
// ──────────────────────────────────────────────────────────

/**
 * Run a slash command and stream SSE events. Because the endpoint is POST,
 * we read the response body as a stream and parse SSE frames manually.
 *
 * Returns an abort function. Calls onEvent(eventName, data) per frame.
 */
export function streamConsole(command, onEvent, onError, onDone) {
    const controller = new AbortController();

    (async () => {
        try {
            const res = await fetch(`${API_BASE}/console/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command }),
                signal: controller.signal,
            });
            if (!res.ok || !res.body) {
                const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
                onError?.(err.error || `HTTP ${res.status}`);
                return;
            }
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            for (;;) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const frames = buffer.split('\n\n');
                buffer = frames.pop() ?? '';
                for (const frame of frames) {
                    let ev = null, data = null;
                    for (const line of frame.split('\n')) {
                        if (line.startsWith('event: ')) ev = line.slice(7).trim();
                        else if (line.startsWith('data: ')) {
                            try { data = JSON.parse(line.slice(6)); } catch { /* ignore */ }
                        }
                    }
                    if (ev) onEvent(ev, data);
                }
            }
            onDone?.();
        } catch (e) {
            if (e.name !== 'AbortError') onError?.(e.message);
        }
    })();

    return () => controller.abort();
}

export const getLibraryMemos = () => apiFetch(`${API_BASE}/library/memos`);

// ──────────────────────────────────────────────────────────
// Screener
// ──────────────────────────────────────────────────────────

export const runScreener = (spec) =>
    apiFetch(`${API_BASE}/screener/run`, { method: 'POST', body: JSON.stringify(spec) });

export const getScreenerFields = () => apiFetch(`${API_BASE}/screener/fields`);

export const getSavedScreeners = () => apiFetch(`${API_BASE}/screener/saved`);

export const saveScreener = (name, rules) =>
    apiFetch(`${API_BASE}/screener/saved`, { method: 'POST', body: JSON.stringify({ name, rules }) });

export const deleteSavedScreener = (id) =>
    apiFetch(`${API_BASE}/screener/saved/${id}`, { method: 'DELETE' });

// ──────────────────────────────────────────────────────────
// Settings — data tier + dashboard layout
// ──────────────────────────────────────────────────────────

export const getDataTier = () => apiFetch(`${API_BASE}/settings/data-tier`);

export const getDashboardLayout = () => apiFetch(`${API_BASE}/dashboard/layout`);

export const saveDashboardLayout = (layout) =>
    apiFetch(`${API_BASE}/dashboard/layout`, { method: 'POST', body: JSON.stringify({ layout }) });

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

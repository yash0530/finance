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

    eventSource.addEventListener('pipeline_start', (e) => {
        callbacks.onPipelineStart?.(JSON.parse(e.data));
    });

    eventSource.addEventListener('stage_start', (e) => {
        callbacks.onStageStart?.(JSON.parse(e.data));
    });

    eventSource.addEventListener('stage_complete', (e) => {
        callbacks.onStageComplete?.(JSON.parse(e.data));
    });

    eventSource.addEventListener('stage_error', (e) => {
        callbacks.onStageError?.(JSON.parse(e.data));
    });

    eventSource.addEventListener('report_complete', (e) => {
        callbacks.onReportComplete?.(JSON.parse(e.data));
        eventSource.close();
    });

    eventSource.onerror = (e) => {
        // EventSource auto-reconnects, but we want to surface fatal errors
        if (eventSource.readyState === EventSource.CLOSED) {
            callbacks.onError?.({ error: 'Connection closed' });
        }
    };

    // Return cleanup function
    return () => {
        eventSource.close();
    };
}

export const getResearchHistory = (ticker, limit = 10) =>
    apiFetch(`${API_BASE}/research/reports/${encodeURIComponent(ticker)}?limit=${limit}`);

export const getAllResearchHistory = (limit = 50) =>
    apiFetch(`${API_BASE}/research/reports?limit=${limit}`);

export const getResearchReportById = (reportId) =>
    apiFetch(`${API_BASE}/research/report/${encodeURIComponent(reportId)}`);


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

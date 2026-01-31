const API_BASE = 'http://localhost:5001/api';

export async function fetchCompanies(sortBy = 'forward_pe', order = 'asc') {
    const response = await fetch(`${API_BASE}/companies?sort_by=${sortBy}&order=${order}`);
    if (!response.ok) throw new Error('Failed to fetch companies');
    return response.json();
}

export async function fetchSectors() {
    const response = await fetch(`${API_BASE}/sectors`);
    if (!response.ok) throw new Error('Failed to fetch sectors');
    return response.json();
}

export async function fetchCompaniesBySector(sector) {
    const response = await fetch(`${API_BASE}/companies/${encodeURIComponent(sector)}`);
    if (!response.ok) throw new Error('Failed to fetch sector companies');
    return response.json();
}

export async function fetchStats() {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
}

export async function searchCompanies(query) {
    const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Failed to search companies');
    return response.json();
}

export async function fetchCompanyByTicker(ticker) {
    const response = await fetch(`${API_BASE}/company/${encodeURIComponent(ticker)}`);
    if (!response.ok) throw new Error('Failed to fetch company');
    return response.json();
}

export async function refreshData() {
    const response = await fetch(`${API_BASE}/refresh`, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to refresh data');
    return response.json();
}

export async function healthCheck() {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error('API not available');
    return response.json();
}

export async function fetchStockHistory(ticker, refresh = false) {
    const params = refresh ? '?refresh=true' : '';
    const response = await fetch(`${API_BASE}/company/${encodeURIComponent(ticker)}/history${params}`);
    if (!response.ok) throw new Error('Failed to fetch stock history');
    return response.json();
}

export async function fetchFinancials(ticker, refresh = false) {
    const params = refresh ? '?refresh=true' : '';
    const response = await fetch(`${API_BASE}/company/${encodeURIComponent(ticker)}/financials${params}`);
    if (!response.ok) throw new Error('Failed to fetch financials');
    return response.json();
}

export async function fetchSpotlight() {
    const response = await fetch(`${API_BASE}/spotlight`);
    if (!response.ok) throw new Error('Failed to fetch spotlight companies');
    return response.json();
}

// Sector color mapping
export const SECTOR_COLORS = {
    'Information Technology': '#3b82f6',
    'Health Care': '#10b981',
    'Financials': '#f59e0b',
    'Consumer Discretionary': '#ec4899',
    'Industrials': '#8b5cf6',
    'Consumer Staples': '#06b6d4',
    'Energy': '#ef4444',
    'Utilities': '#14b8a6',
    'Real Estate': '#6366f1',
    'Materials': '#f97316',
    'Communication Services': '#a855f7'
};

export function getSectorColor(sector) {
    return SECTOR_COLORS[sector] || '#6b7280';
}

// Format helpers
export function formatCurrency(value) {
    if (!value) return 'N/A';
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
}

export function formatPercent(value) {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
}

export function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return 'N/A';
    return Number(value).toFixed(decimals);
}

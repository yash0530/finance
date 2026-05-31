// @ts-check
import { test, expect } from '@playwright/test';

const samplePatterns = {
    title: 'Technical Patterns',
    universe: 'sp500',
    evaluated: 3,
    limit: 3,
    summary: {
        total_patterns: 2,
        bullish_patterns: 1,
        bearish_patterns: 1,
    },
    pattern_types: {
        double_bottom: {
            name: 'Double Bottom',
            signal: 'bullish',
            count: 1,
            patterns: [{
                ticker: 'AAPL',
                company_name: 'Apple Inc.',
                pattern_type: 'double_bottom',
                pattern_name: 'Double Bottom',
                signal: 'bullish',
                confidence: 82,
                current_price: 190,
                current_price_fmt: '$190.00',
                target_price: 220,
            }],
        },
        double_top: {
            name: 'Double Top',
            signal: 'bearish',
            count: 1,
            patterns: [{
                ticker: 'MSFT',
                company_name: 'Microsoft Corp.',
                pattern_type: 'double_top',
                pattern_name: 'Double Top',
                signal: 'bearish',
                confidence: 67,
                current_price: 430,
                current_price_fmt: '$430.00',
                target_price: 390,
            }],
        },
    },
};

function chartBars() {
    return Array.from({ length: 40 }, (_, i) => {
        const close = 180 + i * 0.35;
        return {
            time: `2026-04-${String((i % 28) + 1).padStart(2, '0')}T00:00:00`,
            open: close - 1,
            high: close + 2,
            low: close - 2,
            close,
        };
    });
}

async function mockBackend(page) {
    await page.route('http://localhost:5001/api/**', async (route) => {
        const url = new URL(route.request().url());
        const path = url.pathname;
        let body = {};

        if (path === '/api/version') {
            body = { git_sha: 'patterns-e2e' };
        } else if (path === '/api/patterns/all' || path === '/api/patterns/double_bottom' || path === '/api/patterns/double-bottom') {
            body = samplePatterns;
        } else if (path === '/api/stock/AAPL/header') {
            body = { data: { name: 'Apple Inc.', current_price: 190, analyst_target: 220, market_cap: 2900000000000 } };
        } else if (path === '/api/chart/AAPL') {
            body = { data: { bars: chartBars(), overlays: {} } };
        } else if (path === '/api/stock/AAPL/fundamentals') {
            body = { fundamentals: { data: { market_cap: 2900000000000, forward_pe: 28, revenue_growth: 0.06 } }, trends: { data: { quarter_count: 0 } } };
        } else if (path === '/api/stock/AAPL/technicals') {
            body = {
                data: {
                    current_price: 190,
                    rsi: 45,
                    macd: { macd: 1.2, signal: 0.8, histogram: 0.4, signal_label: 'bullish_cross' },
                    bollinger: { upper: 198, middle: 188, lower: 178, position: 0.6 },
                    year_return_pct: 12,
                    annualized_volatility_pct: 22,
                    relative_strength_vs_spy: 1.08,
                    patterns: [{
                        type: 'double_bottom',
                        name: 'Double Bottom',
                        signal: 'bullish',
                        confidence: 82,
                        current_price: 190,
                        neckline: 205,
                        target_price: 220,
                    }],
                },
            };
        } else if (path === '/api/stock/AAPL/ownership') {
            body = { institutional: { data: { top_holders: [] } }, insider: { data: { total_buys: 0, total_sells: 0 } } };
        } else if (path === '/api/stock/AAPL/filings') {
            body = { ticker: 'AAPL', filings: [], count: 0 };
        } else if (path === '/api/terminal/news') {
            body = { data: { items: [] } };
        } else if (path === '/api/catalysts') {
            body = { catalysts: [] };
        } else if (path === '/api/terminal/flow') {
            body = { degraded: true, reason: 'No flow provider configured', free_tier: 'Mocked e2e response' };
        } else if (path === '/api/themes/by-ticker/AAPL') {
            body = { themes: [] };
        } else if (path === '/api/terminal/watchlist') {
            body = { items: [] };
        }

        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(body),
        });
    });
}

test.describe('Technical Patterns workflow', () => {
    test.beforeEach(async ({ page }) => {
        await mockBackend(page);
    });

    test('renders the restored scanner with summary, filters, and rows', async ({ page }) => {
        await page.goto('/#patterns');

        await expect(page.getByRole('heading', { name: 'Technical Patterns' })).toBeVisible();
        await expect(page.getByText(/3 tickers scanned .* 2 patterns found/)).toBeVisible();
        await expect(page.getByRole('button', { name: /Double Bottom 1/ })).toBeVisible();
        await expect(page.getByRole('cell', { name: 'AAPL', exact: true })).toBeVisible();
        await expect(page.getByRole('cell', { name: 'MSFT', exact: true })).toBeVisible();

        await page.getByRole('button', { name: 'Bearish' }).click();
        await expect(page.getByRole('cell', { name: 'MSFT', exact: true })).toBeVisible();
        await expect(page.getByRole('cell', { name: 'AAPL', exact: true })).toHaveCount(0);
    });

    test('opens Stock View from a pattern row and shows pattern detail', async ({ page }) => {
        await page.goto('/#patterns');

        await page.getByRole('row', { name: /AAPL/ }).click();

        await expect(page).toHaveURL(/#stock\?t=AAPL/);
        await expect(page.getByRole('heading', { name: 'AAPL', exact: true })).toBeVisible();
        await expect(page.locator('#stock-pattern-details')).toContainText('Double Bottom', { timeout: 10_000 });
        await expect(page.locator('#stock-pattern-details')).toContainText('+15.79% target');
    });
});

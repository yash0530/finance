// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Terminal dashboard — full 7-panel scan (Phase 2).
 *
 * Asserts every panel shell mounts. Data population depends on the backend +
 * network; we only require the panel shells to render so the test is stable
 * offline. The Hypotheses panel exposes a per-ticker Generate button (AI on
 * demand) — we assert the panel renders, not that it spends.
 */
const PANELS = [
    '#panel-movers',
    '#panel-theme-heat',
    '#panel-watchlist',
    '#panel-hypotheses',
    '#panel-catalysts',
    '#panel-news',
    '#panel-flow',
];

test.describe('Terminal — daily scan panels', () => {
    test('renders all seven panels', async ({ page }) => {
        await page.goto('/#terminal');
        for (const sel of PANELS) {
            await expect(page.locator(sel)).toBeVisible({ timeout: 10_000 });
        }
    });

    test('watchlist panel has an add-ticker input', async ({ page }) => {
        await page.goto('/#terminal');
        await expect(page.locator('#watchlist-add-input')).toBeVisible({ timeout: 10_000 });
    });

    test('flow panel renders (degraded state on free tier)', async ({ page }) => {
        await page.goto('/#terminal');
        await expect(page.locator('#panel-flow')).toContainText(/degraded|flow|UNUSUAL/i, { timeout: 10_000 });
    });
});

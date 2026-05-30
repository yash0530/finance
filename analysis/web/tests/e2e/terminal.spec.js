// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Terminal dashboard — Phase 1 panels (Movers, Watchlist, News Tape).
 *
 * Asserts the three panels mount with their refresh affordances. Data
 * population depends on the backend + network; we only require the panel
 * shells to render so the test is stable offline.
 */
test.describe('Terminal — daily scan panels', () => {
    test('renders Movers, Watchlist, and News Tape panels', async ({ page }) => {
        await page.goto('/#terminal');
        await expect(page.locator('#panel-movers')).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#panel-watchlist')).toBeVisible();
        await expect(page.locator('#panel-news')).toBeVisible();
    });

    test('watchlist panel has an add-ticker input', async ({ page }) => {
        await page.goto('/#terminal');
        await expect(page.locator('#watchlist-add-input')).toBeVisible({ timeout: 10_000 });
    });
});

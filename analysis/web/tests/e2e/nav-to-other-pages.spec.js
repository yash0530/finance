// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Regression: adding the v2 page should not have broken the rest of the app.
 *
 * For every primary nav item, click it and assert SOMETHING visible renders
 * (any h1, or a recognizable page card). Each page is lazy-loaded so we wait
 * briefly for the Suspense fallback to resolve.
 */
const PAGES = [
    { id: 'nav-portfolio',     label: 'Portfolio' },
    { id: 'nav-research',      label: 'Quick Research' },
    { id: 'nav-watchlist',     label: 'Watchlist' },
    { id: 'nav-rebalance',     label: 'Rebalance' },
    { id: 'nav-alerts',        label: 'Alerts' },
];

test.describe('Nav regression — other pages still render', () => {
    for (const { id, label } of PAGES) {
        test(`${label} renders something visible`, async ({ page }) => {
            await page.goto('/');
            await page.locator(`#${id}`).click();

            // Wait for Suspense fallback to disappear and a heading to mount.
            // Any h1 (page title) is enough — we're guarding against blank screens.
            const heading = page.locator('h1');
            await expect(heading.first()).toBeVisible({ timeout: 10_000 });
        });
    }
});

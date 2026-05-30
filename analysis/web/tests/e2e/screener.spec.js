// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Screener — rule builder + results table.
 *
 * Verifies the builder renders with default rules and that running a screen
 * populates the results table (or its empty state). Depends on the backend for
 * the actual screen; we assert the results container appears.
 */
test.describe('Screener', () => {
    test('rule builder renders with default rules and run button', async ({ page }) => {
        await page.goto('/#screener');
        await expect(page.getByRole('heading', { name: 'Screener' })).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#screener-run-btn')).toBeVisible();
    });

    test('running a screen shows a results table', async ({ page }) => {
        await page.goto('/#screener');
        await page.locator('#screener-run-btn').click();
        await expect(page.locator('#screener-results')).toBeVisible({ timeout: 30_000 });
    });

    test('saved screens panel renders', async ({ page }) => {
        await page.goto('/#screener');
        await expect(page.getByText('Saved screens')).toBeVisible({ timeout: 10_000 });
    });
});

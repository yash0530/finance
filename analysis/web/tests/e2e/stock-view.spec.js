// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Stock View — full cockpit (Phase 3): header, chart with overlay toggles,
 * fundamentals, ownership, filings/news timeline, theme context, CTA bar.
 *
 * Sections lazy-fetch in parallel and fail independently; we assert the section
 * shells mount. Data depends on backend + network.
 */
test.describe('Stock View — single-ticker cockpit', () => {
    test('opens via hash deep-link and shows all sections', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await expect(page.getByRole('heading', { name: 'NVDA' })).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#stock-chart')).toBeVisible();
        await expect(page.locator('#section-fundamentals')).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#section-ownership')).toBeVisible();
        await expect(page.locator('#section-timeline')).toBeVisible();
        await expect(page.locator('#section-theme-context')).toBeVisible();
        await expect(page.locator('#cta-run-thesis')).toBeVisible();
    });

    test('chart overlay toggles render without re-fetch error', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await expect(page.locator('#stock-chart')).toBeVisible({ timeout: 10_000 });
        // Toggle MA20 and BB — buttons live inside the chart card.
        await page.locator('#stock-chart').getByRole('button', { name: 'MA20' }).click();
        await page.locator('#stock-chart').getByRole('button', { name: 'BB' }).click();
        await expect(page.locator('#stock-chart')).toBeVisible();
    });

    test('Run thesis CTA deep-links to Console with command pre-filled', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await page.locator('#cta-run-thesis').click();
        await expect(page.locator('#console-command-input')).toHaveValue(/\/thesis NVDA/, { timeout: 10_000 });
    });
});

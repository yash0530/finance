// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Stock View — full cockpit: header, custom technical chart,
 * fundamentals, ownership, filings/news timeline, theme context, CTA bar.
 *
 * Sections lazy-fetch in parallel and fail independently; we assert the section
 * shells mount. Data depends on backend + network.
 */
test.describe('Stock View — single-ticker cockpit', () => {
    test('opens via hash deep-link and shows all sections', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await expect(page.getByRole('heading', { name: 'NVDA', exact: true })).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#stock-chart')).toBeVisible();
        await expect(page.locator('#section-fundamentals')).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#section-ownership')).toBeVisible();
        await expect(page.locator('#section-timeline')).toBeVisible();
        await expect(page.locator('#section-theme-context')).toBeVisible();
        await expect(page.locator('#cta-run-thesis')).toBeVisible();
    });

    test('custom chart shell renders without blocking the local research panels', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await expect(page.locator('#stock-chart')).toBeVisible({ timeout: 10_000 });
        await expect(page.getByRole('heading', { name: 'Price & Technicals' })).toBeVisible();
        await expect(page.locator('#section-technicals')).toBeVisible({ timeout: 10_000 });
    });

    test('Run thesis CTA opens Research with ticker pre-filled', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await page.locator('#cta-run-thesis').click();
        await expect(page).toHaveURL(/#research\?t=NVDA/);
        await expect(page.locator('#deep-research-input')).toHaveValue('NVDA', { timeout: 10_000 });
    });
});

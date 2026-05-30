// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Stock View — Phase 1 cockpit (header + chart + CTA bar).
 *
 * Deep-links via hash route (#stock?t=NVDA) and verifies the chart range
 * controls and the Console deep-link CTA render.
 */
test.describe('Stock View — single-ticker cockpit', () => {
    test('opens via hash deep-link and shows chart + CTA', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await expect(page.getByRole('heading', { name: 'NVDA' })).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#stock-chart')).toBeVisible();
        await expect(page.locator('#cta-run-thesis')).toBeVisible();
    });

    test('Run thesis CTA deep-links to Console with command pre-filled', async ({ page }) => {
        await page.goto('/#stock?t=NVDA');
        await page.locator('#cta-run-thesis').click();
        await expect(page.locator('#console-command-input')).toHaveValue(/\/thesis NVDA/, { timeout: 10_000 });
    });
});

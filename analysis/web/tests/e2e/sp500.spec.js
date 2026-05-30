// @ts-check
import { test, expect } from '@playwright/test';

/**
 * S&P 500 revival — restored Market cockpit, theme-heat sector toggle,
 * seeded presets, and the pattern/scan screener affordances.
 */
test.describe('S&P 500 revival', () => {
    test('Theme Heat panel toggles to S&P sectors', async ({ page }) => {
        await page.goto('/#terminal');
        const panel = page.locator('#panel-theme-heat');
        await expect(panel).toBeVisible({ timeout: 10_000 });
        await panel.getByRole('button', { name: 'S&P Sectors' }).click();
        // Subtitle updates to "<N> S&P sectors" once the sector heat resolves.
        await expect(panel.getByText(/\d+ S&P sectors/)).toBeVisible({ timeout: 45_000 });
    });

    test('seeded S&P presets appear in saved screens', async ({ page }) => {
        await page.goto('/#screener');
        await expect(page.getByText('Saved screens')).toBeVisible({ timeout: 10_000 });
        await expect(page.getByRole('button', { name: '52-Week Highs (S&P)' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Oversold S&P Large Caps' })).toBeVisible();
    });

    test('Market page exposes the rich S&P cockpit and company table', async ({ page }) => {
        await page.goto('/#market');
        await expect(page.getByRole('heading', { name: 'S&P 500 Intelligence' })).toBeVisible({ timeout: 10_000 });
        await expect(page.getByRole('heading', { name: 'Spotlight Companies' })).toBeVisible({ timeout: 30_000 });
        await page.locator('#nav-market').click();
        await page.locator('#btn-all-companies').click();
        await expect(page.locator('.company-table')).toBeVisible({ timeout: 30_000 });
    });

    test('pattern field exposes a pattern dropdown', async ({ page }) => {
        await page.goto('/#screener');
        await expect(page.getByRole('heading', { name: 'Screener' })).toBeVisible({ timeout: 10_000 });
        // Target the rule's field select (the one that offers a "pattern" option),
        // not the universe select.
        const fieldSelect = page.locator('select.select')
            .filter({ has: page.locator('option[value="pattern"]') }).first();
        await fieldSelect.selectOption('pattern');
        await expect(page.locator('option[value="head_shoulders"]')).toHaveCount(1);
    });
});

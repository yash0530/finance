// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Settings — LLM / Data Tiers / Themes tabs.
 */
test.describe('Settings', () => {
    test('tab switcher renders all three tabs', async ({ page }) => {
        await page.goto('/#settings');
        await expect(page.locator('#settings-tab-llm')).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#settings-tab-tiers')).toBeVisible();
        await expect(page.locator('#settings-tab-themes')).toBeVisible();
    });

    test('data tiers tab shows the free tier as live', async ({ page }) => {
        await page.goto('/#settings');
        await page.locator('#settings-tab-tiers').click();
        await expect(page.getByRole('heading', { name: 'Data tiers' })).toBeVisible({ timeout: 10_000 });
        await expect(page.getByText(/Free \(yfinance/)).toBeVisible();
    });

    test('themes tab lists seeded theme packs', async ({ page }) => {
        await page.goto('/#settings');
        await page.locator('#settings-tab-themes').click();
        await expect(page.getByText('Create theme')).toBeVisible({ timeout: 10_000 });
    });
});

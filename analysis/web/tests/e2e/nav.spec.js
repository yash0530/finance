// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Navigation — 6-page sidebar (Edge terminal) + Docs footer.
 *
 * Each page is lazy-loaded; we assert a heading renders to guard against blank
 * screens. Tests degrade gracefully when the backend is not running — they
 * only assert the client-side shell mounts.
 */
const PAGES = [
    { id: 'nav-terminal', label: 'Terminal' },
    { id: 'nav-console',  label: 'Console' },
    { id: 'nav-library',  label: 'Library' },
    { id: 'nav-screener', label: 'Screener' },
    { id: 'nav-settings', label: 'Settings' },
];

test.describe('Navigation — Edge 6-page nav', () => {
    test('sidebar shows all primary nav items + docs footer', async ({ page }) => {
        await page.goto('/');
        for (const { id } of PAGES) {
            await expect(page.locator(`#${id}`)).toBeVisible();
        }
        await expect(page.locator('#nav-stock')).toBeVisible();
        await expect(page.locator('#nav-docs')).toBeVisible();
    });

    for (const { id, label } of PAGES) {
        test(`${label} renders a heading`, async ({ page }) => {
            await page.goto('/');
            await page.locator(`#${id}`).click();
            await expect(page.locator('h1').first()).toBeVisible({ timeout: 10_000 });
        });
    }

    test('default route is Terminal', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('heading', { name: 'Terminal' })).toBeVisible({ timeout: 10_000 });
    });
});

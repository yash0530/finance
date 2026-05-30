// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Navigation — reconciled sidebar + Docs footer.
 *
 * Each page is lazy-loaded; we assert a heading renders to guard against blank
 * screens. Tests degrade gracefully when the backend is not running — they
 * only assert the client-side shell mounts.
 */
const PAGES = [
    { id: 'nav-market',   heading: 'S&P 500 Intelligence' },
    { id: 'nav-research', heading: 'Deep Research' },
    { id: 'nav-terminal', heading: 'Terminal' },
    { id: 'nav-console',  heading: 'Console' },
    { id: 'nav-library',  heading: 'Library' },
    { id: 'nav-screener', heading: 'Screener' },
    { id: 'nav-settings', heading: 'Settings' },
];

test.describe('Navigation — Edge reconciled nav', () => {
    test('sidebar shows all primary nav items + docs footer', async ({ page }) => {
        await page.goto('/');
        for (const { id } of PAGES) {
            await expect(page.locator(`#${id}`)).toBeVisible();
        }
        await expect(page.locator('#nav-stock')).toBeVisible();
        await expect(page.locator('#nav-docs')).toBeVisible();
    });

    for (const { id, heading } of PAGES) {
        test(`${id} renders a heading`, async ({ page }) => {
            await page.goto('/');
            await page.locator(`#${id}`).click();
            await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible({ timeout: 10_000 });
        });
    }

    test('default route is Market', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('heading', { name: 'S&P 500 Intelligence', exact: true })).toBeVisible({ timeout: 10_000 });
    });
});

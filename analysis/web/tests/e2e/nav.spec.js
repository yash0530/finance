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
    { id: 'nav-discover', heading: 'Daily Scan' },
    { id: 'nav-research', heading: 'Deep Research' },
    { id: 'nav-console',  heading: 'Console' },
    { id: 'nav-library',  heading: 'Library' },
    { id: 'nav-settings', heading: 'Settings' },
];

// Discovery surfaces are now tabs inside the single Discover page.
const DISCOVER_TABS = [
    { id: 'discover-tab-terminal', heading: 'Daily Scan' },
    { id: 'discover-tab-market',   heading: 'S&P 500 Intelligence' },
    { id: 'discover-tab-screener', heading: 'Screener' },
    { id: 'discover-tab-patterns', heading: 'Technical Patterns' },
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

    test('sidebar can collapse to a compact rail', async ({ page }) => {
        await page.goto('/');
        await page.locator('#sidebar-collapse-toggle').click();
        await expect(page.locator('.app-shell')).toHaveClass(/sidebar-is-collapsed/);
        await expect(page.locator('#nav-discover')).toBeVisible();
        await expect(page.locator('#nav-discover .nav-label')).toBeHidden();
        await expect(page.locator('#nav-discover .nav-short')).toBeVisible();
    });

    for (const { id, heading } of PAGES) {
        test(`${id} renders a heading`, async ({ page }) => {
            await page.goto('/');
            await page.locator(`#${id}`).click();
            await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible({ timeout: 10_000 });
        });
    }

    test('Discover folds the four discovery surfaces into tabs', async ({ page }) => {
        await page.goto('/');
        await page.locator('#nav-discover').click();
        for (const { id, heading } of DISCOVER_TABS) {
            await page.locator(`#${id}`).click();
            await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible({ timeout: 10_000 });
        }
    });

    test('default route is Discover (Daily Scan)', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('heading', { name: 'Daily Scan', exact: true })).toBeVisible({ timeout: 10_000 });
    });

    test('sidebar groups nav into Discover / Research / Track', async ({ page }) => {
        await page.goto('/');
        for (const label of ['Discover', 'Research', 'Track']) {
            await expect(page.locator('.sidebar-section-label', { hasText: label })).toBeVisible();
        }
    });

    test('global ticker entry routes to Stock View on Enter', async ({ page }) => {
        await page.goto('/');
        await page.locator('#global-ticker-input').fill('AAPL');
        await page.locator('#global-ticker-input').press('Enter');
        await expect(page).toHaveURL(/stock.*t=AAPL/);
    });

    test('global ticker entry R-> routes to Research', async ({ page }) => {
        await page.goto('/');
        await page.locator('#global-ticker-input').fill('AAPL');
        await page.locator('#global-ticker-research').click();
        await expect(page).toHaveURL(/research.*t=AAPL/);
        await expect(page.getByRole('heading', { name: 'Deep Research', exact: true })).toBeVisible({ timeout: 10_000 });
    });
});

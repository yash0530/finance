// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Sidebar + Deep Research v2 navigation sanity check.
 *
 * Verifies the v2 page renders with the required form controls
 * (input, budget selector) so downstream tests can rely on them.
 */
test.describe('Navigation — Deep Research v2', () => {
    test('sidebar shows main nav items and v2 page renders', async ({ page }) => {
        await page.goto('/');

        // Sidebar items present.
        await expect(page.getByRole('button', { name: /Deep Research v2/ })).toBeVisible();
        await expect(page.getByRole('button', { name: /Deep Research(?! v2)/ })).toBeVisible();
        await expect(page.getByRole('button', { name: /Portfolio/ })).toBeVisible();

        // Navigate to v2.
        await page.locator('#nav-deep-research-v2').click();

        // Heading rendered (emoji + text).
        await expect(page.getByRole('heading', { name: /Deep Research v2/ })).toBeVisible();

        // Input and budget selector present.
        await expect(page.locator('#deep-research-v2-input')).toBeVisible();
        await expect(page.locator('#budget-profile')).toBeVisible();

        // Submit button rendered (disabled until ticker typed).
        await expect(page.locator('#btn-deep-research-v2')).toBeVisible();
    });
});

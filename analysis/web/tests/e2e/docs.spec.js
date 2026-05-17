// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Docs page — verify in-app guides render and basic navigation works.
 *
 * Loads the page, asserts the left sidebar shows the 5 guides, clicks
 * each one, and checks that the body content updates with the title.
 */
test.describe('Docs page — in-app guides', () => {
    const EXPECTED_GUIDES = [
        'Getting Started',
        'How to Invest with This Tool',
        'Understanding the Outputs',
        'Troubleshooting',
        'Architecture Overview',
    ];

    test('docs page lists all guides and renders content on click', async ({ page }) => {
        await page.goto('/');
        await page.locator('#nav-docs').click();

        // The docs left nav should show every expected title.
        for (const title of EXPECTED_GUIDES) {
            await expect(page.locator('.docs-nav-item', { hasText: title }).first())
                .toBeVisible({ timeout: 10_000 });
        }

        // Click each guide and verify the body shows an H1 with the same title.
        for (const title of EXPECTED_GUIDES) {
            await page.locator('.docs-nav-item', { hasText: title }).first().click();
            await expect(page.locator('.markdown-body .md-h1', { hasText: title }))
                .toBeVisible({ timeout: 5_000 });
        }
    });

    test('docs page renders TOC for the current guide', async ({ page }) => {
        await page.goto('/');
        await page.locator('#nav-docs').click();

        // First doc loads by default — TOC card should appear with at least one entry.
        await expect(page.locator('.markdown-body').first()).toBeVisible({ timeout: 10_000 });
        // The right-hand "On this page" rail should have at least one h2 link.
        const tocLinks = page.locator('aside >> text=On this page').locator('..').locator('a');
        await expect(tocLinks.first()).toBeVisible({ timeout: 5_000 });
    });
});

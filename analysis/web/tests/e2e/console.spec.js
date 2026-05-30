// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Console — slash-command bar + SSE stream.
 *
 * We exercise the client wiring without spending on the LLM: an unknown command
 * streams back a console_error frame, which the UI renders as an error alert.
 * This proves the POST-SSE plumbing (fetch reader → frame parse → render) works
 * end-to-end against the backend.
 */
test.describe('Console — slash commands', () => {
    test('command bar and hints render', async ({ page }) => {
        await page.goto('/#console');
        const input = page.locator('#console-command-input');
        await expect(input).toBeVisible({ timeout: 10_000 });
        await input.click();
        await expect(page.getByText('/compare <A> <B> <C>')).toBeVisible();
    });

    test('unknown command streams an error frame', async ({ page }) => {
        await page.goto('/#console');
        const input = page.locator('#console-command-input');
        await input.fill('/bogus NVDA');
        await page.locator('#console-run-btn').click();
        await expect(page.locator('.alert-error')).toBeVisible({ timeout: 10_000 });
    });

    test('run button disabled until a command is typed', async ({ page }) => {
        await page.goto('/#console');
        await expect(page.locator('#console-run-btn')).toBeDisabled();
        await page.locator('#console-command-input').fill('/why NVDA');
        await expect(page.locator('#console-run-btn')).toBeEnabled();
    });
});

test.describe('Library — reports + memos tabs', () => {
    test('tab switcher renders both tabs', async ({ page }) => {
        await page.goto('/#library');
        await expect(page.locator('#library-tab-reports')).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('#library-tab-memos')).toBeVisible();
        await page.locator('#library-tab-memos').click();
        // Memos tab renders (either memo cards or an empty-state heading).
        await expect(page.locator('.page-title').first()).toBeVisible();
    });
});

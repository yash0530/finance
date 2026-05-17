// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Confirms the Deep Research v2 form is wired end-to-end on the client.
 *
 * We do NOT require the LLM/backend to be configured — the test passes as
 * long as submitting the form transitions into ANY observable "we tried"
 * state: streaming button label, an error alert, or any SSE-driven card
 * (planner / tool call / debate) appearing.
 */
test.describe('Deep Research v2 form submission', () => {
    test.setTimeout(15_000);

    test('typing a ticker and clicking Research kicks off a request', async ({ page }) => {
        await page.goto('/');
        await page.locator('#nav-deep-research-v2').click();

        const input = page.locator('#deep-research-v2-input');
        const budget = page.locator('#budget-profile');
        const submit = page.locator('#btn-deep-research-v2');

        await expect(input).toBeVisible();
        await input.fill('NVDA');
        await budget.selectOption('quick');
        await expect(submit).toBeEnabled();

        await submit.click();

        // Any of these signals = the form was wired correctly:
        //   1. Button shows "Researching…" (streaming state)
        //   2. An error alert renders (LLM not configured, network error, etc.)
        //   3. An SSE-driven card appears (planner, tool call, debate, verdict)
        const streamingBtn = page.getByRole('button', { name: /Researching/ });
        const errorAlert = page.locator('.alert-error');
        const sseCard = page.locator(
            'text=/Planner round|Sector:|Memo v|Judge Verdict|Living Memo/',
        );

        await expect(
            streamingBtn.or(errorAlert).or(sseCard).first(),
        ).toBeVisible({ timeout: 10_000 });
    });
});

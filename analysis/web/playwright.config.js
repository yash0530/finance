// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for Edge UAT.
 *
 * - Boots Vite dev server (npm run dev on :5173) automatically.
 * - Backend Flask (port 5001) must be started manually before running tests
 *   (see tests/e2e/README.md). Tests are written to degrade gracefully when
 *   the backend or LLM is not configured.
 * - Chromium only to keep the setup minimal — no firefox/webkit.
 */
export default defineConfig({
    testDir: './tests/e2e',
    timeout: 60_000,
    expect: { timeout: 5_000 },
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: 0,
    workers: 1,
    reporter: [['list']],
    use: {
        baseURL: 'http://localhost:5173',
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        video: 'off',
        actionTimeout: 5_000,
        navigationTimeout: 15_000,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: {
        command: 'npm run dev',
        cwd: '.',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
        stdout: 'pipe',
        stderr: 'pipe',
    },
});

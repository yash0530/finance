# Portfolio Intelligence v2 — Playwright UAT

Browser-level UAT for the React frontend, focused on the **Deep Research v2**
surface introduced in `feat: Implement Next-Gen AI Portfolio Intelligence & Deep
Research Terminal`. Backend SSE / agent-loop behavior is covered by pytest in
`analysis/tests/test_agent_loop.py` — these tests assert the **UI is wired
correctly**, not that the LLM produces a specific verdict.

## How to run

```bash
cd analysis/web
npm run test:e2e
```

The Vite dev server is started automatically by `playwright.config.js`
(`webServer` block on `http://localhost:5173`). You do not need to run
`npm run dev` separately.

## Prerequisites (one-time)

1. **Install npm devDependency** (already declared in `package.json`):
   ```bash
   cd analysis/web
   npm install
   ```
2. **Install Playwright browsers** (manual — not run automatically because the
   sandboxed dev environment cannot download them):
   ```bash
   npx playwright install chromium
   ```
3. **Start the Flask backend** in a separate terminal so SSE / `/api/*` calls
   succeed:
   ```bash
   cd analysis
   python3 app.py    # listens on :5001
   ```
   Tests are written to **degrade gracefully** when the backend is down or no
   LLM is configured (see `v2-research-form.spec.js`) — they assert "the
   request was attempted," not that a full report came back.

## What's covered

| Spec | What it asserts |
|---|---|
| `nav.spec.js` | Sidebar renders the v2 entry; clicking it shows the heading, ticker input (`#deep-research-v2-input`) and budget selector (`#budget-profile`). |
| `v2-research-form.spec.js` | Typing `NVDA`, picking the **Quick** budget profile, and clicking **Research** triggers *some* observable outcome — the streaming button, an error alert, or an SSE-driven card. 15s test timeout. |
| `nav-to-other-pages.spec.js` | Regression: Portfolio, Quick Research, Watchlist, Rebalance, Alerts still render an `<h1>` after the v2 addition (no blank screens). |

## Discovering tests without running them

```bash
cd analysis/web
npx playwright test --list
```

This parses the spec files only — useful for verifying the config is valid even
when browsers aren't installed yet.

## Layout

```
analysis/web/
├── playwright.config.js         # config: chromium-only, webServer = vite dev
└── tests/e2e/
    ├── README.md                # this file
    ├── nav.spec.js              # sidebar + v2 page render
    ├── v2-research-form.spec.js # form submission wiring
    └── nav-to-other-pages.spec.js # regression on other pages
```

# Edge Personal Markets Terminal — Architecture

> **Status**: v3.1 security cleanup
> **Last updated**: 2026-05-30
> **Audience**: Engineers and contributors. For user behavior, see [`deep_research_guide.md`](./deep_research_guide.md).

## Intent

Edge is a pull-based research terminal for a single investor. It focuses on
market scanning, ticker inspection, cited Deep Research, Living Memo history,
and calibration. It does not ingest private positions, account data, or local
secret files.

## Navigation

`Market` (default S&P 500 cockpit) · `Stock View` · `Research` · `Daily Scan` ·
`Console` · `Library` · `Screener` · `Review` · `Patterns` · `Settings` · `Docs`.

## Backend

- Flask app: `analysis/app.py` on `:5001`
- SQLite: `~/.edge_terminal/finance.db` with WAL enabled
- Deep Research: `analysis/agent_loop.py`
- Console dispatcher: `analysis/console_orchestrator.py`
- Data tools: `analysis/tools/`
- Living Memo: `analysis/living_memo.py`
- Settings: provider/model/base URL only; API keys are never stored in SQLite

## Frontend

- React 18 + Vite in `analysis/web/`
- Route shell: `src/App.jsx`
- Navigation: `src/components/Sidebar.jsx`
- API client: `src/utils/api.js`
- Pages are lazy-loaded from `src/pages/`

## Secret Handling

Secrets must be supplied through the parent process environment, not project
files and not SQLite. The app intentionally does not load `analysis/.env`, and
the settings API rejects key persistence.

Remote LLM providers read:

- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`

Optional data integrations read their own environment variables at call time and
must degrade gracefully when absent. Endpoints may report whether a tier is live,
but must never return secret values.

## SQLite Schema

Core tables:

```text
watchlist
research_cache
llm_settings
research_reports
living_memo
living_memo_versions
living_memo_staged
tool_call_log
recommendations
catalysts
transcripts_cache
insider_trades_cache
institutional_holdings_cache
options_metrics_cache
tool_result_cache
sector_classification_cache
monitoring_digest
monitoring_enabled
themes
theme_tickers
hypotheses_cache
screener_saved
dashboard_layout
```

Do not store raw API credentials, private positions, account credentials, or
copied `.env` content in any table.

## Deep Research Flow

1. Load Living Memo and sector profile.
2. Planner selects Tools using open questions and required sector evidence.
3. Tool calls run under budget and record sources into the evidence ledger.
4. Bull, Bear, Bull Rebuttal, Judge, and Self-Critique synthesize a verdict.
5. Memo Synth proposes a staged Living Memo update.
6. Report, tool log, and calibration row are persisted when allowed.

Every LLM-emitted claim must cite `evidence_refs`; validators should stay strict.

## Pull-Based Rule

All refreshes are user-triggered. Do not add background workers, cron jobs,
queues, push notifications, or silent sync loops.

Daily Scan uses `/api/terminal/snapshot` as its morning-refresh envelope. The
snapshot gathers quote coverage, movers, theme heat, catalysts, news, provider
health, and flow status into one response so panels do not independently hammer
the same providers. Quote-backed panels share the `quote_snapshot` tool, which
uses a short live cache and stale-good fallback when yfinance throttles or fails.

Flow is always on demand. The no-ticker Daily Scan flow panel reports provider
status only. Per-ticker flow can show free yfinance options-chain metrics, while
Unusual Whales-only data remains gated by `UNUSUAL_WHALES_API_KEY`. Rate-limit
responses trip a short cooldown instead of retrying repeatedly.

## Tool Contract

Each Tool returns a `ToolResult` with:

- `data`: JSON-serializable dict
- `sources`: one or more `Source` entries for cited fields
- `confidence`: `high`, `medium`, or `low`
- `cost_usd`: actual spend
- `cached`: whether the result came from cache

New data fetches belong in `analysis/tools/<name>.py` and must register through
`tools/__init__.py`.

## Testing

- Backend: `cd analysis && python3 -m pytest tests/`
- Frontend UAT: `cd analysis/web && npx playwright test`
- New tools need mocked network tests.
- Agent/orchestration changes need `tests/test_agent_loop.py` coverage.
- New UI surfaces need Playwright specs.

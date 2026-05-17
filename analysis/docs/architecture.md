---
title: Architecture Overview
order: 5
category: Reference
---

# Architecture Overview

The engineering view of Portfolio Intelligence — for when you want to know *why* a number is the way it is, or when something breaks and you need to trace it.

For the full engineering spec, see `next_gen_tool.md` in the repo. This page is the abridged tour.

---

## Two research surfaces

| | Quick Research | Deep Research |
|---|---|---|
| Pipeline | Fixed 8-stage | Agentic loop |
| Files | `research_engine.py`, `research_stream.py` | `agent_loop.py`, `agents/`, `analyzers/` |
| Output | Single report | Verdict + Living Memo + evidence ledger |
| Endpoint | `/api/research/<ticker>/stream` | `/api/research/<ticker>/v2/stream` |
| Use when | Fast triage | Anything you plan to trade |

Both surfaces coexist. Quick Research is a fast triage path; Deep Research is the analytical depth path. The user picks per-research which one to run.

---

## Backend stack

- **Flask** on `:5001` (`analysis/app.py`) — routes only; business logic lives in service modules.
- **SQLite** at `~/.portfolio_intelligence/finance.db` (WAL mode) — single source of truth for portfolio, research, recommendations, monitoring digests, calibration outcomes.
- **LLM abstraction** in `analysis/llm_service.py` — Claude / Gemini / Ollama, with `_get_provider_and_model(task_type)` routing fast vs. deep tasks to different models.
- **Background workers** (started on app boot):
  - `alert_worker.py` — price alerts
  - `monitoring_worker.py` — hourly thesis decay
  - `outcome_worker.py` — daily recommendation outcome backfill

---

## Frontend stack

- **React 18 + Vite** in `analysis/web/`.
- Pages are **lazy-loaded** from `src/pages/`.
- All API calls go through `src/utils/api.js` — one place to add headers, handle errors, swap base URLs.
- **Dark terminal aesthetic** — `src/index.css` defines the palette; new components inherit it.

---

## The agent loop (Deep Research)

The orchestrator is `agent_loop.py`. One research session runs:

```
1. Sector router classify   → picks the analyzer (saas/banks/biotech/etc.)
2. Planner agent             → picks the next batch of tools to call
3. Tool executor             → calls the tools, collects ToolResults
   (loop 2-3 up to MAX_PLANNER_ITERATIONS or until budget exhausted)
4. Bull agent                → writes the long case from the ledger
5. Bear agent                → writes the short case from the ledger
6. Judge agent               → picks a verdict + sizing + targets
7. Self-critique agent       → audits the judge's reasoning for holes
8. Memo synth agent          → folds new findings into the Living Memo
```

Streamed as SSE events; each event is named in `next_gen_tool.md` §events.

The **Budget** (`tools.Budget`) enforces per-session caps:
- Dollar cap (`max_usd`) — short-circuits if exceeded.
- Wall-clock cap (`max_wall_clock_sec`) — short-circuits if exceeded.

Every LLM call goes through the agent loop so the Budget tracks spend. Standalone `provider.complete(...)` calls in new code are forbidden (see `CLAUDE.md`).

---

## Tools

Every data fetch is a `Tool` (`analysis/tools/<name>.py`). The contract:

- Subclasses `tools.Tool`.
- Returns a `ToolResult` with `data`, `sources` (one Source per cited field), `confidence`, and `cost_usd`.
- Auto-registered via the `_AUTOLOAD` list in `tools/__init__.py`.

Current tool inventory: fundamentals, financial_trends, technicals, dcf_valuation, qoe_forensics, peer_compare, macro_context, sentiment, insider_activity, institutional_holdings, options_metrics, earnings_transcripts, sec_filings, news_catalysts, analyst_estimates, sector_kpis.

---

## Sector analyzers

Each sector has a dedicated analyzer in `analysis/analyzers/` (saas, banks, reits, biotech, energy, semis, consumer, generic). Each analyzer exposes:

- `required_tools()` — tools the planner should prioritize for this sector.
- `kpi_template()` — sector-specific KPIs (NRR for SaaS, NIM for banks, etc.).
- `peer_cohort(ticker)` — peer list for benchmarking.
- `prompt_prefix()` — sector context the bull/bear/judge agents prepend to their system prompts.

The sector_router classifies tickers → analyzer key. Classification flow:
1. Cache hit (DB).
2. Rule-based on GICS sector + industry.
3. **LLM fallback** when rules don't match — one cheap call, cached forever.
4. Default fallback if LLM unavailable.

---

## The Living Memo

Per-ticker evolving knowledge document in `living_memo.py`. Why distillation over RAG:

- A new research session loads the prior memo, identifies what's stale or unresolved, investigates that, and writes a refined version.
- Compounds expertise: your 50th NVDA session is genuinely deeper than your first.
- Auditable: every version is persisted (`living_memo_versions`); history is the user's audit trail and must not be deleted.
- Open questions populate the Advisor dashboard's "outstanding research questions" section.

---

## Calibration

`recommendations` table stores every deep research verdict with entry price, conviction, thesis_summary, and what_would_change_mind. `outcome_worker.py` runs daily and backfills `outcome_1m_return_pct`, `outcome_3m_return_pct`, `outcome_6m_return_pct`, `outcome_1y_return_pct`.

The Calibration page (`/api/advisor/calibration`) aggregates hit rate by recommendation type and conviction band. Local-LLM verdicts are **excluded** from calibration so the track record measures the underlying model, not a mix.

---

## Caching

Each tool sets its own `cache_ttl_seconds`. Cached results live in:
- `tool_result_cache` (generic) — fundamentals, trends, technicals, sentiment, peer_compare, macro_context, etc.
- Bespoke tables for heavier data: `transcripts_cache`, `insider_trades_cache`, `institutional_holdings_cache`, `options_metrics_cache`.

The agent loop's `force_refresh=True` flag bypasses all caches for a single session.

---

## Where things live

```
analysis/
├── app.py                  Flask routes (quick + deep research + advisor + docs)
├── agent_loop.py           Deep research orchestrator + SSE streaming
├── agents/                 bull, bear, judge, self_critique, planner, memo_synth
├── analyzers/              per-sector specialization
├── tools/                  data fetches + computations
├── llm_service.py          multi-provider LLM abstraction
├── living_memo.py          per-ticker evolving memo
├── sector_router.py        ticker → sector classification
├── monitoring_worker.py    hourly thesis-decay daemon
├── outcome_worker.py       daily recommendation outcome backfill
├── rebalancing_engine.py   holdings-aware rebalance signals
├── docs/                   in-app guides (this directory)
└── tests/                  pytest suite
```

---

## What NOT to touch

- Core DB tables: `portfolio_holdings`, `watchlist`, `alerts`, `research_cache`, `research_reports`, `llm_settings`.
- `living_memo_versions` rows — append-only, never delete.
- Functions in `research_engine.py` — they back quick research endpoints and are wrapped as Tools; the originals stay.

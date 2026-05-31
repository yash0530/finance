---
title: Architecture Overview
order: 5
category: Reference
---

# Architecture Overview

The engineering view of Edge. For the full source-of-truth spec, see `next_gen_tool.md`; this page is the abridged tour.

---

## Research architecture

The primary research path is **Deep Research**, launched from Console slash commands and backed by `/api/research/<ticker>/v2/stream`.

- **Orchestrator**: `agent_loop.py`
- **Agents**: planner, bull, bear, judge, self_critique, memo_synth
- **Tools**: `analysis/tools/`, each returning citation-aware `ToolResult` objects
- **Specialization**: `sector_router.py` and `analysis/analyzers/`
- **Memory**: `living_memo.py`, with append-only memo versions

One session runs:

```text
1. Sector router classifies the ticker
2. Planner chooses tool batches
3. Tool executor collects cited evidence
4. Bull agent writes the long case
5. Bear agent writes the short case
6. Judge agent emits verdict, sizing, targets, and risks
7. Self-critique audits the reasoning
8. Memo synth proposes Living Memo updates
```

The loop is dynamic: planner and executor may iterate until the budget, wall-clock cap, or evidence requirements are satisfied.

---

## Backend stack

- **Flask** on `:5001` (`analysis/app.py`) — routes only; logic belongs in service modules and tools.
- **SQLite** at `~/.edge_terminal/finance.db` (WAL mode) — schema in `db.py`.
- **LLM abstraction** in `llm_service.py` — provider/model routing for fast and deep tasks.
- **Tools** in `analysis/tools/` — all new data fetches must live here and register through `tools/__init__.py`.
- **Pull-based execution** — data refreshes happen only when requested by the user or an endpoint call.

Core DB tables such as `research_reports`, `living_memo*`, and `llm_settings` are treated as stable. New features should add sibling tables rather than altering or deleting core history.

---

## Frontend stack

- **React + Vite** in `analysis/web/`.
- Pages are lazy-loaded from `src/pages/`.
- All API calls go through `src/utils/api.js`.
- Current first-class pages: Terminal, Stock View, Console, Library, Screener, Settings.

The UI is optimized for repeated research work: dense panels, clear controls, fast navigation, and direct access to the actual research surfaces.

---

## Console and SSE

Console commands are dispatched by `console_orchestrator.py`:

- `/thesis <ticker>` — full Deep Research and Living Memo flow.
- `/dossier <ticker>` — richer context pack for a ticker.
- `/why <ticker>` — quick cited explanation.
- `/theme <slug>` — theme-level research.
- `/compare <tickers>` — relative analysis across names.

The backend streams progress via SSE. The event vocabulary is documented in `next_gen_tool.md` so frontend handlers and agent output stay aligned.

---

## Tools and citations

Every data fetch or derived computation is a `Tool`. The contract:

- Subclass `tools.Tool`.
- Return a `ToolResult` with `data`, `sources`, `confidence`, `cost_usd`, and optional `error`.
- Degrade gracefully when data is missing.
- Cite source fields precisely enough for the agents and UI to verify claims.

Representative tools include fundamentals, financial trends, technicals, price history, movers, news tape, theme heat, S&P 500 lookup/refresh, DCF, QoE forensics, SEC filings, insider Form 4, 13F holders, options flow, transcripts, catalysts, peer compare, and macro context.

---

## Screener and S&P 500 snapshot

`screener_engine.py` scans saved rules against themes, watchlist, or the cached S&P 500 snapshot. Fast S&P rules use `.cache/sp500_data.json`; live pattern scans are opt-in because they fetch per-ticker price history.

The snapshot is refreshed through the `sp500_refresh` Tool and `POST /api/market/refresh-sp500`. It preserves the existing cache shape so `sp500_lookup`, Screener, and theme heat can read the same file.

---

## Living Memo

The Living Memo is the per-ticker memory layer. It is distillation, not retrieval:

- A new session reads the prior memo.
- The agent investigates stale facts and open questions.
- Memo synth proposes an updated version.
- Every version is preserved in `living_memo_versions`.

Never delete memo history; it is the audit trail.

---

## Caching

Tool cache TTLs are set per tool. Generic cached tool output lives in `tool_result_cache`; heavier sources may use dedicated cache tables or files. `force_refresh=True` on a research run bypasses tool caches for that session.

The S&P 500 snapshot is file-backed because it is shared by fast screeners and sector heat. Refresh it from Settings when freshness matters.

---

## Where things live

```text
analysis/
├── app.py                  Flask routes
├── agent_loop.py           Deep Research orchestration + SSE
├── agents/                 planner, bull, bear, judge, critique, memo synth
├── analyzers/              sector-specialized KPI templates and cohorts
├── tools/                  data fetches and computations
├── console_orchestrator.py Console slash-command dispatcher
├── screener_engine.py      rule-based screener
├── living_memo.py          per-ticker evolving memo
├── sector_router.py        ticker to sector classification
├── themes_service.py       theme pack CRUD
├── db.py                   schema and CRUD
├── docs/                   in-app guides
└── tests/                  pytest suite
```

---

## What not to touch lightly

- Core DB history tables.
- `living_memo_versions` rows.
- Citation validators and evidence-reference requirements.
- The preserved `research_engine.py` helpers that Tools still wrap.

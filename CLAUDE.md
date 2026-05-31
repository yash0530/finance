# Edge Personal Markets Terminal — Repo Guide for Claude

> Read this first. Architecture details: `analysis/docs/next_gen_tool.md`. User behavior: `analysis/docs/deep_research_guide.md`.

## Identity
Single-investor research and decision-support tool. The owner is deploying $10K of personal capital against Deep Research output — quality and honest calibration matter more than feature breadth or surface polish.

## Stack one-liners
- **Backend**: Flask on `:5001` (`analysis/app.py`). SQLite at `~/.edge_terminal/finance.db` (WAL mode). LLM abstraction in `analysis/llm_service.py` (Claude / Gemini / Ollama).
- **Frontend**: React 18 + Vite (`analysis/web/`). All API calls go through `src/utils/api.js`. Pages are lazy-loaded from `src/pages/`.
- **Run**: `analysis/start.sh` boots backend and frontend. Tests: `cd analysis && python3 -m pytest tests/`.

## Research surface
One primary research path: **Deep Research** — agentic loop in `agent_loop.py` + multi-agent debate in `agents/` + Living Memo in `living_memo.py` + per-sector specialization in `analyzers/`. Endpoint `/api/research/<ticker>/v2/stream`, driven from the Console (`console_orchestrator.py`).

`research_engine.py` is preserved as a dependency for Tools (several tools call its fetch helpers). Pattern detectors live in `pattern_detectors.py`.

## Golden rules
1. **Never commit API keys.** They're in `.gitignore` — keep them there.
2. **Never alter core DB tables** (`research_reports`, `living_memo*`, `llm_settings`). Additive only — new tables for new features.
3. **Never delete `living_memo_versions` rows.** The memo history is the user's audit trail; loss is unrecoverable.
4. **New data fetches must be Tools.** Add to `analysis/tools/<name>.py` and the autoload list in `tools/__init__.py`. Don't inline fetches in `app.py` or agents.
5. **Every LLM-emitted claim must cite evidence.** Bull/Bear/Judge prompts require `evidence_refs`. Don't soften the validators.
6. **Respect the budget.** All new LLM calls flow through `agent_loop` so `Budget` enforces cost ceilings. No standalone `provider.complete(...)` calls in new code.
7. **No `pip install` without updating `analysis/requirements.txt`.** Same for `npm install` and `analysis/web/package.json`.
8. **Pull-based only.** No background workers, cron, queues, alerts, or push notifications.

## Current nav pages (Edge v3)
`Terminal` · `Stock View` · `Console` · `Library` · `Screener` · `Settings` (+ `Docs` footer)

## Where things live
- `analysis/agent_loop.py` — orchestrator + SSE streaming + `run_deep_research()`
- `analysis/agents/` — bull, bear, judge, self_critique, planner, memo_synth
- `analysis/tools/` — all data fetches; each subclasses `Tool` and `register()`s itself
- `analysis/analyzers/` — sector-specialized KPI templates and peer cohorts
- `analysis/living_memo.py` — per-ticker evolving knowledge document
- `analysis/sector_router.py` — ticker → sector classification
- `analysis/console_orchestrator.py` — slash-command dispatcher (Console)
- `analysis/themes_service.py` · `analysis/seed_themes.py` — theme packs
- `analysis/screener_engine.py` — rule-based screener
- `analysis/db.py` — single source of truth for schema; `init_db()` runs on import
- `analysis/docs/next_gen_tool.md` — architecture spec (engineering)
- `analysis/docs/deep_research_guide.md` — power-user docs (UX/behavior)
- `analysis/tests/` — pytest suite (189 tests as of last run)
- `analysis/web/tests/e2e/` — Playwright browser UAT

## Doc-code drift
If runtime behavior diverges from the docs, the docs are the source of truth for *intent*. Either fix the code to match, or update the doc in the same change. Never leave them silently desynced.

## Testing expectation
- Every new tool gets a unit test in `analysis/tests/test_*` with mocked network/LLM.
- Agent / orchestration changes get integration tests in `tests/test_agent_loop.py`.
- New UI surfaces get a Playwright spec in `analysis/web/tests/e2e/`.
- Run `python3 -m pytest tests/` before declaring done. Suite should stay green.

## Memory & feedback
Persistent memory lives in `~/.claude/projects/-Users-yash-Desktop-Programming-finance/memory/`. Two facts to internalize across sessions:
- The user prefers **distillation over RAG** for per-ticker memory (this is why we have Living Memo, not a vector store).
- The tool's output is acted on with real money — be honest about model limits, recommend conservative sizing until calibration is earned.

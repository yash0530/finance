# Edge Personal Markets Terminal — Repo Guide for Gemini

> Read this first. Architecture details: `analysis/docs/next_gen_tool.md`. User behavior: `analysis/docs/deep_research_guide.md`.

## Identity
Single-investor research and decision-support tool. The owner is deploying $10K of personal capital against Deep Research output — quality and honest calibration matter more than feature breadth or surface polish.

## Stack Overview
- **Backend**: Flask on `:5001` (`analysis/app.py`). SQLite at `~/.edge_terminal/finance.db` (WAL mode). LLM abstraction in `analysis/llm_service.py` (Codex / Gemini / Ollama).
- **Frontend**: React 18 + Vite (`analysis/web/`). All API calls go through `src/utils/api.js`. Pages are lazy-loaded from `src/pages/`.
- **Run**: `analysis/start.sh` boots backend and frontend. Tests: `cd analysis && python3 -m pytest tests/`.

## Golden Rules
1. **Never commit API keys.** Keep them in environment variables.
2. **Never alter core DB tables** (`research_reports`, `living_memo*`, `llm_settings`). Additive only.
3. **Never delete `living_memo_versions` rows.** The memo history is the user's audit trail; loss is unrecoverable.
4. **New data fetches must be Tools.** Add to `analysis/tools/<name>.py` and autoload list.
5. **Every LLM-emitted claim must cite evidence.** Bull/Bear/Judge prompts require `evidence_refs`.
6. **Respect the budget.** All LLM calls flow through `agent_loop` so `Budget` enforces cost ceilings.
7. **No `pip install` or `npm install` without updating requirements.** Add to `analysis/requirements.txt` or `package.json`.
8. **Pull-based only.** No background workers or automatic push/cron tasks.

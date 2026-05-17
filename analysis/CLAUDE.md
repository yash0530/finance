# analysis/ — Backend Conventions

> See `docs/next_gen_tool.md` for the full v2 architecture. See `../CLAUDE.md` for repo-wide rules.

## Module map

| Module | Owns |
|---|---|
| `app.py` | Flask routes (v1 + v2). Routes only; logic delegated to services. |
| `db.py` | SQLite schema, connection helper, all CRUD. Single source of truth for tables. |
| `agent_loop.py` | v2 orchestrator: planner → executor → debate → memo synth, SSE streaming |
| `agents/` | LLM-facing reasoning agents (bull, bear, judge, self_critique, planner, memo_synth) |
| `tools/` | Data-fetch + computation Tools (citation-aware, budget-aware) |
| `analyzers/` | Per-sector specialization (KPI templates, peer cohorts, prompt prefixes) |
| `living_memo.py` | Per-ticker evolving memo + diff/render helpers |
| `sector_router.py` | Ticker → sector classification (rule-based, cached) |
| `llm_service.py` | Multi-provider LLM abstraction (Claude / Gemini / Ollama) |
| `research_engine.py` | v1 fixed pipeline functions — preserved, not extended |
| `research_stream.py` | v1 SSE — preserved |
| `portfolio_service.py` | Robinhood + CSV ingestion, P&L enrichment |
| `sentiment_service.py` | Finnhub + Reddit + yfinance composite |
| `edgar_service.py` | SEC 10-K/10-Q fetch + section extraction |
| `rebalancing_engine.py` | Risk-profile portfolio analysis |
| `alert_worker.py` | Background daemon polling prices for alert triggers |
| `companies.py` | S&P 500 batch fetch (legacy) |

## Citation contract (v2)

Every `Tool._execute` MUST return a `ToolResult` with:
- `data: dict` — JSON-serializable
- `sources: List[Source]` — one Source per cited field (tool + field + fetched_at + optional url)
- `confidence: "high" | "medium" | "low"`
- `cost_usd: float` — actual spend (0.0 for free APIs)

Tools that internally call the LLM (`requires_llm = True`) must charge the budget accurately. Tools that hit external APIs must handle failures gracefully — return `ToolResult(..., error=str, confidence="low")` rather than raising.

## DB migrations

New tables go in `init_db()` in `db.py` with `IF NOT EXISTS`. Add a corresponding CRUD function group below the table list. **Never alter or drop existing v1 tables.** If you need new columns on a v1 table, create a sibling v2 table instead and join on ticker.

## Testing

- `tests/conftest.py` redirects `HOME` to a tempdir so the test DB is isolated from the user's real one.
- Tools should be tested with mocked HTTP (use `monkeypatch` on `requests` or `yfinance.Ticker`).
- Agent tests use `FakeProvider` (see `tests/test_agent_loop.py`) to avoid LLM API calls.
- Run: `python3 -m pytest tests/`. Suite should stay green.

## External API etiquette

- **SEC EDGAR**: `User-Agent: PortfolioIntelligence research@example.com`. Rate-limit to 10 req/sec (`time.sleep(0.15)` between calls).
- **yfinance**: free but can throttle — cache aggressively (TTLs in `next_gen_tool.md` §21).
- **Finnhub / FMP**: API keys from env vars (`FINNHUB_API_KEY`, `FMP_API_KEY`). Tools must gracefully degrade when keys are absent — never crash.
- **LLM providers**: only call via `llm_service._get_provider_and_model(task_type)`. Never instantiate providers directly from new code.

## Cost guardrail

The `Budget` in `agent_loop` enforces per-session dollar caps. Every new LLM-using tool must:
- Declare `requires_llm = True`
- Implement `estimate_cost()` realistically (in USD)
- Charge `cost_usd` accurately in the returned `ToolResult`

Don't add LLM calls outside `agent_loop`'s budget tracking.

## What NOT to touch in v1

- `research_engine.py` core functions (`fetch_fundamentals`, `fetch_financial_trends`, etc.) — they're wrapped as v2 Tools but the originals stay for v1 endpoints.
- `research_stream.py` — preserved for v1 SSE endpoint.
- v1 schema in `db.py.init_db()` — additive only.

# tools/ — Tool Registry

Every data fetch or computation in v2 is a `Tool`. The LLM never fetches data directly — it asks tools.

## Pattern (mandatory)

See `fundamentals.py` for the canonical example. Each tool:

1. Lives in its own file: `analysis/tools/<name>.py`
2. Subclasses `tools.Tool`
3. Sets class attributes: `name`, `description`, `cache_ttl_seconds`, `requires_llm`
4. Implements `schema() -> dict` returning JSON Schema for args
5. Implements `estimate_cost(**args) -> float` returning USD estimate
6. Implements `_execute(self, **args) -> ToolResult`
7. Calls `register(ClassName())` at module bottom
8. Is added to `_AUTOLOAD` in `__init__.py` (alphabetical by relevance to planner)

```python
class MyTool(Tool):
    name = "my_tool"
    description = "What this returns. Used by the planner LLM to decide when to call."
    cache_ttl_seconds = 3600
    requires_llm = False

    def schema(self): ...
    def estimate_cost(self, **args): ...
    def _execute(self, ticker, **kwargs):
        # check cache → fetch → save cache → return ToolResult with sources
        ...

register(MyTool())
```

## Hard rules

- **Return `ToolResult`, not a dict.** The wrapper catches `TypeError` but the agent loop expects `ToolResult` shape.
- **Populate `sources`.** Every field a downstream agent might cite needs a `Source`. No naked numbers.
- **Set `confidence` honestly.**
  - `high` — directly fetched from a primary source (SEC filing, exchange data)
  - `medium` — derived computation from primary data
  - `low` — LLM-extracted from unstructured text, or degraded (missing data, API failure)
- **Never crash.** Wrap external calls in try/except; return `ToolResult(..., error=str, confidence="low")` instead.
- **Charge `cost_usd` accurately** if `requires_llm = True`. The Budget depends on it.

## Caching

Most tools cache via the generic `tool_result_cache` table:
```python
from db import get_tool_cache, save_tool_cache

cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
if cached:
    return ToolResult(tool_name=self.name, data=cached, sources=..., cached=True)
# ... fetch ...
save_tool_cache(self.name, ticker, data)
```

Tool-specific tables exist for heavier data (`transcripts_cache`, `insider_trades_cache`, `institutional_holdings_cache`, `options_metrics_cache`) — use them when the data is large or you need bespoke queries.

## When to add a tool

- A new data source the planner should be able to call
- A new computation that produces evidence (QoE scores, correlation, stress tests)
- A new view of existing data the LLM benefits from (e.g. "peer rank on margin")

When NOT to add a tool:
- One-off transformations that happen in agent prompts (just inline them)
- UI-only formatting (do that in the React layer)
- Pure aggregation across tools the agent already calls (the agent can do this from the ledger)

## Sector-specific KPIs

If your tool produces sector-relevant data (e.g. NRR for SaaS, NIM for banks), update the corresponding analyzer in `analyzers/` to list it as a required tool. The sector router uses this to prioritize calls.

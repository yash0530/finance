# tools/ — Tool Registry (Rules for AI Assistants)

All data fetches and backend calculations are structured as classes inheriting from `Tool`.

## Tool Checklist
To implement or update a Tool:
1. Define class subclassing `Tool`.
2. Attributes: `name`, `description`, `cache_ttl_seconds`, `requires_llm`.
3. Implement methods: `schema()`, `estimate_cost()`, and `_execute()`.
4. Call `register(ToolClassName())` at the bottom of the module.
5. Append your module to `_AUTOLOAD` in `analysis/tools/__init__.py`.

## Output Contract
You **MUST** return a `ToolResult` object.
- Include a list of `Source` objects to map fields back to their origins (e.g., `sec_filing`, `yahoo_finance`).
- Set `confidence` level:
  - `high`: direct primary source lookup.
  - `medium`: calculated metrics or indicators.
  - `low`: LLM inference or failed API graceful fallback.
- Never crash on API exceptions; catch errors and return `ToolResult(..., error="...")` with low confidence.

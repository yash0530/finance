# tools/ — Tool Registry (Gemini Developer Guide)

This directory contains individual tool implementations that feed the Deep Research loop.

## Integration Rules
- **Autoloading**: Add new tools to `_AUTOLOAD` in `tools/__init__.py`.
- **Caching**: Utilize `get_tool_cache` and `save_tool_cache` from `db.py` to prevent redundant fetches.
- **Robustness**: Implement `try-except` blocks for all external web requests or calculations to ensure tools never crash the main loop.
- **Pricing**: Ensure `estimate_cost` evaluates the true model token cost when a tool utilizes LLM APIs.

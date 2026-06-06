# analysis/ — Backend Conventions (Gemini Developer Guide)

This directory is the Python Flask backend codebase.

- **Stack**: Flask runs on port `:5001`. SQLite database sits at `~/.edge_terminal/finance.db`.
- **Deep Research**: The core engine is orchestrated inside `agent_loop.py` using Server-Sent Events (SSE) to stream execution feedback to React.
- **Budgeting**: Run all model invocations through the budget ceiling tracking to avoid overspending API keys.
- **Cache Management**: Tools cache in `tool_result_cache` table via helper utilities.

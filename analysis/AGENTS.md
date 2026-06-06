# analysis/ — Backend Conventions (Rules for AI Assistants)

The backend directory contains the Flask application, SQLite operations, LLM integrations, and research loops.

## Backend Rules
1. **Flask Isolation**: `app.py` handles route mapping and SSE streaming only. Core business logic belongs in separate services (`llm_service`, `db`, `living_memo`, etc.) or custom tools.
2. **Database Integrity**: Never drop or alter columns in `db.py`. Ensure tables are added with `IF NOT EXISTS` in `init_db()`.
3. **LLM Abstraction**: Always dispatch LLM requests using the `llm_service.py` wrapper, which dynamically queries models from SQLite configuration and manages budgets.
4. **Tool registry**: New data fetch integrations must subclass `Tool` and register in `analysis/tools/__init__.py`.
5. **No Background Worker Threads**: Keep executions pull-based, driven entirely by requests.

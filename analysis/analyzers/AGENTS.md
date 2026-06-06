# analyzers/ — Sector-Specific Analyzers (Rules for AI Assistants)

Sector Analyzers configure GICS sector templates.

## Developer Rules
- **Method Alignment**: Make sure all fields defined in the dictionary returned by `kpi_template()` map to tool extraction capabilities.
- **Keep Prompts Compact**: The `prompt_prefix()` should be concise to avoid consuming excessive token budget.
- **Router Mapping**: Update the classification dict in `analysis/sector_router.py` when adding a new analyzer module.

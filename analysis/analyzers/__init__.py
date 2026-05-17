"""
analysis.analyzers — sector-specific analyzers.

Each module here exports a `SectorAnalyzer` class with:
  - sector_key, sector_name
  - required_tools() — tool names the planner should prioritize
  - kpi_template() — sector KPIs to extract
  - peer_cohort(ticker) — curated peer list for comparison
  - prompt_prefix() — sector-specific system-prompt prefix prepended to
    Bull/Bear/Judge prompts

The sector_router selects which analyzer to use based on GICS industry.
The default fallback is `generic.SectorAnalyzer`.
"""

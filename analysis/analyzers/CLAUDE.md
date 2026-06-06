# analyzers/ — Sector-Specific Analyzers

This directory contains sector specialized metrics and cohorts to tune the deep research loop for different GICS industries.

## Contract
Each module MUST export a `SectorAnalyzer` class containing:
- `sector_key`: Identifier string.
- `sector_name`: Human-readable name.
- `required_tools() -> List[str]`: Tools the planner should run first.
- `kpi_template() -> Dict[str, Dict[str, str]]`: Custom KPIs to extract (e.g. ARR for SaaS, NIM for banks).
- `peer_cohort(ticker) -> List[str]`: Cohort tickers for relative comparisons.
- `prompt_prefix() -> str`: Prompt prefix to prepend to Bull/Bear/Judge instructions.

## Adding a Sector Analyzer
1. Create `analysis/analyzers/<sector_key>.py`.
2. Implement the `SectorAnalyzer` class matching the interface.
3. Register the router mapping in `analysis/sector_router.py`.

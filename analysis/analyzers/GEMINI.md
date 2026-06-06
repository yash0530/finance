# analyzers/ — Sector-Specific Analyzers (Gemini Developer Guide)

This directory contains sector specific metrics templates.

- **Routing & Selection**: Classifications are selected by GICS sub-industry mappings. Look at `analysis/sector_router.py` to see the parsing.
- **Default Fallback**: If a ticker does not match any specialized analyzer, it defaults to `generic.py`.
- **Peer Cohort**: Make sure all peer ticker lists defined under `_PEERS` are populated with active, high-volume names of similar business models.

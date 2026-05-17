"""
analyzers.energy — oil & gas / energy analyzer.

Energy theses are commodity-cycle bets layered on company-specific reserves,
breakeven economics, and hedging. Macro regime (oil curve, USD) dominates.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "energy"
    sector_name = "Energy / Oil & Gas"

    _PEERS = ["XOM", "CVX", "COP", "EOG", "PSX", "MPC", "VLO"]

    def required_tools(self) -> List[str]:
        return ["macro_context"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "proved_reserves": {
                "description": "Proved reserves in BOE — asset base",
                "extract_from": "edgar_filings",
                "good_range": "10+ years of production at current rates",
            },
            "breakeven_price": {
                "description": "Wellhead breakeven $/bbl for new wells",
                "extract_from": "transcripts",
                "good_range": "<$40/bbl (durable through cycles)",
            },
            "production_growth": {
                "description": "BOE/day production growth YoY",
                "extract_from": "financial_trends",
                "good_range": "Mid-single-digits with capital discipline",
            },
            "fd_costs": {
                "description": "Finding & Development cost per BOE",
                "extract_from": "edgar_filings",
                "good_range": "<$10/BOE (Tier-1 acreage)",
            },
            "hedging_pct": {
                "description": "% of next-12-months production hedged",
                "extract_from": "transcripts",
                "good_range": "30-60% (balanced cash-flow vs upside)",
            },
            "net_debt_to_ebitda": {
                "description": "Leverage at mid-cycle price assumptions",
                "extract_from": "fundamentals",
                "good_range": "<1.5x at mid-cycle (cycle-resilient)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing energy, frame the thesis against the oil/gas commodity "
            "curve and USD regime first, then layer in company-specific reserves, "
            "wellhead breakeven, production growth, F&D costs, and hedge book. "
            "Capital discipline (buybacks > production growth) is the post-2020 "
            "norm — penalize companies that overspend on capex. Mid-cycle balance "
            "sheet matters more than current cash flow."
        )

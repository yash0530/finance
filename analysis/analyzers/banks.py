"""
analyzers.banks — large-cap bank & capital-markets analyzer.

KPIs target the rate-sensitivity / credit-quality / capital triangle that
drives bank earnings power.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "banks"
    sector_name = "Banks & Capital Markets"

    _PEERS = ["JPM", "BAC", "WFC", "C", "GS", "MS", "PNC", "TFC"]

    def required_tools(self) -> List[str]:
        return ["qoe_forensics", "macro_context"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "nim": {
                "description": "Net Interest Margin — spread between asset yield and funding cost",
                "extract_from": "fundamentals",
                "good_range": ">2.8% (US large-cap baseline)",
            },
            "efficiency_ratio": {
                "description": "Non-interest expense / revenue — operating leverage",
                "extract_from": "financial_trends",
                "good_range": "<60% (best-in-class), <65% (acceptable)",
            },
            "npl_ratio": {
                "description": "Non-performing loans / total loans — credit quality",
                "extract_from": "edgar_filings",
                "good_range": "<1% (benign credit cycle)",
            },
            "deposit_beta": {
                "description": "Sensitivity of deposit cost to rate changes",
                "extract_from": "transcripts",
                "good_range": "<40% (sticky deposit franchise)",
            },
            "tier_1_capital": {
                "description": "CET1 ratio — regulatory capital strength",
                "extract_from": "edgar_filings",
                "good_range": ">11% (above SCB requirement)",
            },
            "rotce": {
                "description": "Return on Tangible Common Equity — profitability per dollar of capital",
                "extract_from": "fundamentals",
                "good_range": ">15% (best-in-class)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing a bank, prioritize Net Interest Margin trajectory, "
            "deposit beta vs the rate cycle, efficiency ratio (operating leverage), "
            "NPL trends (credit quality), Tier 1 capital (capital return capacity), "
            "and ROTCE (profitability per capital dollar). Always frame the thesis "
            "against the rate regime and credit cycle — same bank behaves very "
            "differently in different macro states."
        )

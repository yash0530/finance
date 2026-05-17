"""
analyzers.reits — Real-estate investment trust analyzer.

REIT economics revolve around FFO/AFFO (the cash-flow proxy that replaces
GAAP earnings), occupancy, lease structure, and cap-rate spread vs Treasury.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "reits"
    sector_name = "REITs / Real Estate"

    _PEERS = ["O", "PLD", "EQIX", "AMT", "CCI", "SPG", "AVB"]

    def required_tools(self) -> List[str]:
        return ["macro_context"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "ffo": {
                "description": "Funds From Operations — REIT-specific earnings proxy",
                "extract_from": "financial_trends",
                "good_range": ">5% YoY growth in same-store FFO",
            },
            "affo": {
                "description": "Adjusted FFO — distributable cash flow after maintenance capex",
                "extract_from": "financial_trends",
                "good_range": "AFFO payout ratio <85% for safety",
            },
            "occupancy": {
                "description": "Occupied square footage / total — demand health",
                "extract_from": "transcripts",
                "good_range": ">95% (Class A), >90% (general)",
            },
            "walt": {
                "description": "Weighted Average Lease Term — visibility on cash flows",
                "extract_from": "edgar_filings",
                "good_range": ">7 years (industrial/office), >5y (retail)",
            },
            "cap_rate_spread": {
                "description": "Property cap rate minus 10Y Treasury — risk premium",
                "extract_from": "macro_context",
                "good_range": ">200bps (attractive), <100bps (rich)",
            },
            "lease_ladder": {
                "description": "Distribution of lease expirations across years",
                "extract_from": "edgar_filings",
                "good_range": "<15% of leases expiring in any single year",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing a REIT, ignore GAAP earnings and focus on FFO/AFFO "
            "trajectory, AFFO payout coverage, same-store occupancy, weighted "
            "average lease term, and the cap-rate-vs-Treasury spread. REIT prices "
            "move with the 10Y yield — always anchor the thesis to the rate regime "
            "and refinancing wall. A REIT looks cheap on P/E but expensive on "
            "AFFO yield in a rising-rate world."
        )

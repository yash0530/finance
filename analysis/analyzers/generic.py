"""
analyzers.generic — default fallback analyzer.

Used when no specialized analyzer matches the ticker's GICS industry.
Sector key is `"default"`.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "default"
    sector_name = "Generic / Cross-sector"

    def required_tools(self) -> List[str]:
        # No sector-specific additions; the default tool list applies.
        return []

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "revenue_growth": {
                "description": "YoY revenue growth — top-line trajectory",
                "extract_from": "financial_trends",
                "good_range": ">10% (growth), 5-10% (steady), <0% (concerning)",
            },
            "operating_margin": {
                "description": "Operating income / revenue — core profitability",
                "extract_from": "fundamentals",
                "good_range": ">15% (strong), >25% (best-in-class)",
            },
            "roe": {
                "description": "Return on Equity — capital efficiency",
                "extract_from": "fundamentals",
                "good_range": ">15% (strong)",
            },
            "fcf_margin": {
                "description": "Free cash flow / revenue — cash conversion",
                "extract_from": "financial_trends",
                "good_range": ">10% (cash-generative), >20% (excellent)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        # No fixed cohort for the generic fallback — caller should rely on
        # the peer_compare tool to derive sector averages instead.
        return []

    def prompt_prefix(self) -> str:
        return (
            "For this cross-sector company, focus on revenue growth durability, "
            "operating margin trajectory, return on equity, and free cash flow "
            "conversion. Without a specialized sector lens, lean harder on "
            "peer-compare and qoe_forensics to triangulate quality."
        )

"""
analyzers.consumer — consumer discretionary / staples / retail analyzer.

Consumer KPIs focus on comp sales (same-store growth), inventory turn,
gross-margin spread vs peers, and brand-strength leading indicators.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "consumer"
    sector_name = "Consumer / Retail"

    _PEERS = ["WMT", "COST", "TGT", "AMZN", "HD", "LOW", "MCD", "SBUX"]

    def required_tools(self) -> List[str]:
        return ["sentiment", "alt_data"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "comp_sales": {
                "description": "Same-store sales growth (comparable-store basis)",
                "extract_from": "transcripts",
                "good_range": "Positive low-single-digits (mature), >5% (strong)",
            },
            "inventory_turn": {
                "description": "COGS / average inventory — capital efficiency",
                "extract_from": "financial_trends",
                "good_range": ">8x (best-in-class grocers/discounters)",
            },
            "gross_margin_spread": {
                "description": "Gross margin delta vs peer-cohort median",
                "extract_from": "peer_compare",
                "good_range": ">200bps above cohort (pricing power)",
            },
            "brand_strength": {
                "description": "Search trend / app rank / sentiment leading indicators",
                "extract_from": "alt_data",
                "good_range": "Rising search index, top-tier app rank in category",
            },
            "traffic_vs_ticket": {
                "description": "Comp decomposition: customer count vs basket size",
                "extract_from": "transcripts",
                "good_range": "Traffic-led growth (price-led is fragile)",
            },
            "promotional_intensity": {
                "description": "Discount/promotional cadence vs prior year",
                "extract_from": "transcripts",
                "good_range": "Flat-to-down (rising = margin pressure ahead)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing a consumer or retail name, prioritize comp-store sales "
            "trajectory (decomposed into traffic vs ticket), inventory turn, gross "
            "margin spread vs peer cohort, and alt-data brand-strength signals "
            "(search trends, app rank, sentiment). Watch for rising promotional "
            "intensity as a leading indicator of margin pressure. Distinguish "
            "secular winners from cyclical beneficiaries — both can show good "
            "current numbers but only one repeats next year."
        )

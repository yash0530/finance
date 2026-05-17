"""
analyzers.semis — semiconductors analyzer.

Semi theses turn on the capex cycle, customer concentration (hyperscaler
dependency), wafer pricing, and gross-margin trajectory.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "semis"
    sector_name = "Semiconductors"

    _PEERS = ["NVDA", "AMD", "AVGO", "TSM", "ASML", "AMAT", "LRCX", "KLAC"]

    def required_tools(self) -> List[str]:
        return ["options_flow", "transcripts"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "wafer_pricing": {
                "description": "ASP per wafer / per chip trajectory",
                "extract_from": "transcripts",
                "good_range": "Stable-to-up in cyclical upturn",
            },
            "capex_cycle_position": {
                "description": "Where the company sits in the WFE / fab capex cycle",
                "extract_from": "transcripts",
                "good_range": "Early-mid expansion preferred",
            },
            "customer_concentration": {
                "description": "% revenue from top 1 / top 5 customers",
                "extract_from": "edgar_filings",
                "good_range": "<30% top-1, <60% top-5 (diversified)",
            },
            "lead_times": {
                "description": "Order-to-delivery lead time in weeks",
                "extract_from": "transcripts",
                "good_range": "Extending = demand strong; collapsing = warning",
            },
            "gross_margin": {
                "description": "Gross margin — mix and pricing power",
                "extract_from": "fundamentals",
                "good_range": ">50% (fabless leaders >70%)",
            },
            "inventory_days": {
                "description": "Days of inventory on hand",
                "extract_from": "financial_trends",
                "good_range": "60-90 days (above = channel stuffing risk)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing semiconductors, identify where the company sits in the "
            "capex/inventory cycle, the customer concentration risk (especially "
            "hyperscaler dependency), wafer pricing and lead-time trends, and gross "
            "margin trajectory. Watch for inventory-days expansion as the early "
            "warning of a cycle top. Customer-concentrated names get a multiple "
            "haircut even when current earnings look strong."
        )

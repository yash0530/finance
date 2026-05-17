"""
analyzers.saas — SaaS / cloud software sector analyzer.

KPIs focus on the SaaS rule-of-40 stack: ARR growth, retention quality,
unit economics, and Rule of 40 composite.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "saas"
    sector_name = "Software / SaaS"

    # Curated mega-cap and mid-cap SaaS comparables
    _PEERS = ["CRM", "NOW", "SNOW", "MDB", "NET", "DDOG", "OKTA"]

    def required_tools(self) -> List[str]:
        return ["transcripts", "qoe_forensics"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "arr": {
                "description": "Annualized Recurring Revenue — primary SaaS scale metric",
                "extract_from": "transcripts",
                "good_range": ">25% YoY growth at scale",
            },
            "nrr": {
                "description": "Net Revenue Retention — cohort expansion minus churn",
                "extract_from": "transcripts",
                "good_range": ">120% (best-in-class), >110% (healthy)",
            },
            "rule_of_40": {
                "description": "Revenue growth % + FCF margin % — the SaaS unit economics composite",
                "extract_from": "financial_trends",
                "good_range": ">40 (durable growth-with-margin)",
            },
            "magic_number": {
                "description": "Net new ARR / S&M spend — sales efficiency",
                "extract_from": "transcripts",
                "good_range": ">1.0 (productive S&M), >1.5 (excellent)",
            },
            "cac_payback": {
                "description": "Months to recover customer acquisition cost",
                "extract_from": "transcripts",
                "good_range": "<18 months (healthy), <12 (best-in-class)",
            },
            "gross_retention": {
                "description": "Revenue retained before upsells — churn proxy",
                "extract_from": "transcripts",
                "good_range": ">90% (enterprise), >85% (SMB)",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing a SaaS / cloud-software company, prioritize ARR growth "
            "trajectory, Net Revenue Retention (>110% baseline), Rule of 40 "
            "(growth + FCF margin), CAC payback (<18m), and magic number (>1.0). "
            "Treat decelerating NRR or expanding CAC payback as leading indicators "
            "of weakness even if headline revenue still grows. Discount the multiple "
            "for falling Rule of 40."
        )

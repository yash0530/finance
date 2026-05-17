"""
analyzers.biotech — biotech & pharmaceutical analyzer.

Biotech theses are catalyst-driven (trial readouts, PDUFA dates) and gated by
cash runway. Most pre-revenue names trade on pipeline NPV, not fundamentals.
"""

from typing import Any, Dict, List


class SectorAnalyzer:
    sector_key = "biotech"
    sector_name = "Biotech & Pharma"

    _PEERS = ["MRNA", "BNTX", "REGN", "VRTX", "GILD", "AMGN", "BIIB"]

    def required_tools(self) -> List[str]:
        return ["catalyst_lookup", "transcripts"]

    def kpi_template(self) -> Dict[str, Dict[str, str]]:
        return {
            "pipeline_phase": {
                "description": "Stage distribution of programs (Preclinical / Ph1 / Ph2 / Ph3 / Filed)",
                "extract_from": "edgar_filings",
                "good_range": "Multiple Ph2/Ph3 assets across indications",
            },
            "pdufa_dates": {
                "description": "Upcoming FDA action dates",
                "extract_from": "catalyst_lookup",
                "good_range": "Near-term catalyst within 12 months",
            },
            "cash_runway_quarters": {
                "description": "Quarters of cash at current burn",
                "extract_from": "fundamentals",
                "good_range": ">8 quarters (avoids dilution overhang)",
            },
            "trial_readouts": {
                "description": "Scheduled efficacy/safety data readouts",
                "extract_from": "catalyst_lookup",
                "good_range": "Major readout within 6-9 months",
            },
            "patent_cliff_years": {
                "description": "Time until top product loses exclusivity",
                "extract_from": "edgar_filings",
                "good_range": ">7 years (de-risked)",
            },
            "rd_intensity": {
                "description": "R&D / revenue — pipeline investment",
                "extract_from": "fundamentals",
                "good_range": ">15% (commercial-stage); pre-revenue n/a",
            },
        }

    def peer_cohort(self, ticker: str) -> List[str]:
        return [t for t in self._PEERS if t.upper() != (ticker or "").upper()]

    def prompt_prefix(self) -> str:
        return (
            "When analyzing biotech, anchor the thesis to (a) pipeline NPV — phase, "
            "indication size, probability of approval — and (b) cash runway against "
            "the next catalyst. PDUFA dates, Phase 2/3 readouts, and label expansions "
            "drive 90% of the moves. Pre-revenue names should be sized as binary "
            "bets — never assume linear price action. Always check dilution risk."
        )

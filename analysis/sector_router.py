"""
sector_router.py — Sector classification + analyzer dispatch (Phase 4).

Classifies a ticker into one of: saas, banks, reits, biotech, energy, semis,
consumer, default. Each sector has a dedicated analyzer module under
`analyzers/` that defines required tools, KPIs, a peer cohort, and a
prompt prefix for bull/bear/judge agents.

Classification flow:
  1. Cache hit (db.sector_classification_cache) — if manual_override=1 always trust
  2. Rule-based on GICS sector + industry from yfinance .info
  3. LLM fallback (not implemented in v1 — falls through to "default")
  4. Result cached
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import db

logger = logging.getLogger(__name__)


# ============================================================================
# Analyzer registry
# ============================================================================

def _build_registry() -> Dict[str, Any]:
    """Import each analyzer module at registry-build time."""
    from analyzers import (
        saas, banks, reits, biotech, energy, semis, consumer, generic,
    )
    instances = {}
    for mod in (saas, banks, reits, biotech, energy, semis, consumer, generic):
        try:
            inst = mod.SectorAnalyzer()
            instances[inst.sector_key] = inst
        except Exception as e:
            logger.warning(f"Failed to instantiate analyzer from {mod.__name__}: {e}")
    if "default" not in instances:
        # Hard guarantee: there must always be a default
        instances["default"] = generic.SectorAnalyzer()
    return instances


_ANALYZERS: Dict[str, Any] = _build_registry()


def get_analyzer(sector_key: str):
    """Return the analyzer for the given sector key. Falls back to default."""
    return _ANALYZERS.get(sector_key) or _ANALYZERS["default"]


def available_sectors() -> list:
    return sorted(_ANALYZERS.keys())


# ============================================================================
# Classification rules
# ============================================================================

# Order matters — first match wins. Each rule is (predicate, sector_key).
def _industry_contains(needles):
    needles = [n.lower() for n in needles]
    def _pred(sector: str, industry: str):
        ind = (industry or "").lower()
        sec = (sector or "").lower()
        return any(n in ind for n in needles) or any(n in sec for n in needles)
    return _pred


_RULES = [
    # SaaS / Software
    (_industry_contains(["software—application", "software—infrastructure",
                          "internet software", "saas", "software"]), "saas"),
    # Banks
    (_industry_contains(["banks—diversified", "banks—regional", "capital markets",
                          "banks"]), "banks"),
    # REITs
    (_industry_contains(["reit", "real estate"]), "reits"),
    # Biotech / pharma
    (_industry_contains(["biotechnology", "drug manufacturers",
                          "pharmaceutical"]), "biotech"),
    # Energy
    (_industry_contains(["oil & gas", "energy"]), "energy"),
    # Semis
    (_industry_contains(["semiconductors", "semiconductor equipment"]), "semis"),
    # Consumer
    (_industry_contains(["restaurants", "retail", "specialty retail",
                          "consumer"]), "consumer"),
]


def _rule_based_classify(sector: str, industry: str) -> Optional[str]:
    for pred, key in _RULES:
        try:
            if pred(sector, industry):
                return key
        except Exception:
            continue
    return None


# ============================================================================
# Public API
# ============================================================================

def classify(ticker: str, fundamentals_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Classify a ticker into a sector key.

    Returns:
        {
          "sector_key": str,
          "gics_industry": str,
          "method": "cache" | "rule" | "default",
          "confidence": "high" | "medium" | "low",
          "manual_override": bool,
        }
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {
            "sector_key": "default", "gics_industry": "",
            "method": "default", "confidence": "low",
            "manual_override": False,
        }

    # 1. Cache (always trust manual override)
    cached = db.get_sector_classification(ticker)
    if cached:
        manual = bool(cached.get("manual_override"))
        if manual:
            return {
                "sector_key": cached["sector_key"],
                "gics_industry": cached.get("gics_industry", ""),
                "method": "cache",
                "confidence": "high",
                "manual_override": True,
            }
        # Non-manual cache → trust as well (cheap; classification rarely changes)
        return {
            "sector_key": cached["sector_key"],
            "gics_industry": cached.get("gics_industry", ""),
            "method": "cache",
            "confidence": "medium",
            "manual_override": False,
        }

    # 2. Rule-based using provided fundamentals OR yfinance
    sector_str = ""
    industry_str = ""
    if fundamentals_data:
        sector_str = fundamentals_data.get("sector", "") or ""
        industry_str = fundamentals_data.get("industry", "") or ""
    else:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info or {}
            sector_str = info.get("sector", "") or ""
            industry_str = info.get("industry", "") or ""
        except Exception as e:
            logger.debug(f"yfinance classify lookup failed for {ticker}: {e}")

    rule_key = _rule_based_classify(sector_str, industry_str)
    if rule_key:
        db.save_sector_classification(
            ticker, rule_key, industry_str, method="rule", manual_override=False,
        )
        return {
            "sector_key": rule_key,
            "gics_industry": industry_str,
            "method": "rule",
            "confidence": "high",
            "manual_override": False,
        }

    # 3. Default fallback
    db.save_sector_classification(
        ticker, "default", industry_str, method="default", manual_override=False,
    )
    return {
        "sector_key": "default",
        "gics_industry": industry_str,
        "method": "default",
        "confidence": "low",
        "manual_override": False,
    }


def manual_classify(ticker: str, sector_key: str, gics_industry: str = "") -> Dict[str, Any]:
    """User override — pins the classification regardless of rules."""
    if sector_key not in _ANALYZERS:
        raise ValueError(f"Unknown sector_key: {sector_key}. Valid: {available_sectors()}")
    db.save_sector_classification(
        ticker, sector_key, gics_industry, method="manual", manual_override=True,
    )
    return {
        "sector_key": sector_key,
        "gics_industry": gics_industry,
        "method": "manual",
        "confidence": "high",
        "manual_override": True,
    }

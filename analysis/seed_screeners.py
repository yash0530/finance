"""
seed_screeners.py — idempotent default screener presets.

Called once on boot from db.init_db(), after seed_themes. Mirrors the seed_themes
contract: presets are matched by name, so re-running never duplicates them. Like
the theme seed, a default whose name is absent is re-created on the next boot —
deletions are not tracked (these are starter packs the user can edit freely).

Each preset's stored payload is a full screener spec ({universe, combine, rules,
scan?}) so it runs directly when loaded. Three presets read only the S&P 500
snapshot cache and are fast; three set `scan: true` because they need live
per-ticker technicals or chart-pattern detection across the index (slow, opt-in).
"""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# (name, spec). Pattern values must match tools' pattern_detectors.PATTERN_DETECTORS keys.
DEFAULT_SCREENERS: List[Dict] = [
    {
        "name": "52-Week Highs (S&P)",
        "spec": {
            "universe": "sp500", "combine": "AND",
            "rules": [{"field": "pct_from_52w_high", "op": ">=", "value": -2}],
        },
    },
    {
        "name": "Beaten-Down Large Caps (S&P)",
        "spec": {
            "universe": "sp500", "combine": "AND",
            "rules": [
                {"field": "pct_from_52w_high", "op": "<=", "value": -30},
                {"field": "market_cap", "op": ">=", "value": 10_000_000_000},
            ],
        },
    },
    {
        "name": "Momentum Leaders (S&P)",
        "spec": {
            "universe": "sp500", "combine": "AND",
            "rules": [{"field": "year_change_pct", "op": ">=", "value": 50}],
        },
    },
    {
        "name": "Oversold S&P Large Caps",
        "spec": {
            "universe": "sp500", "combine": "AND", "scan": True,
            "rules": [
                {"field": "rsi", "op": "<", "value": 30},
                {"field": "market_cap", "op": ">=", "value": 10_000_000_000},
            ],
        },
    },
    {
        "name": "Pattern: Head & Shoulders (S&P)",
        "spec": {
            "universe": "sp500", "combine": "AND", "scan": True,
            "rules": [
                {"field": "pattern", "op": "is", "value": "head_shoulders"},
                {"field": "market_cap", "op": ">=", "value": 1_000_000_000},
            ],
        },
    },
    {
        "name": "Pattern: Cup & Handle (S&P)",
        "spec": {
            "universe": "sp500", "combine": "AND", "scan": True,
            "rules": [
                {"field": "pattern", "op": "is", "value": "cup_and_handle"},
                {"field": "market_cap", "op": ">=", "value": 1_000_000_000},
            ],
        },
    },
]


def seed_default_screeners() -> None:
    """Insert default presets whose names aren't already present. Idempotent."""
    import db

    try:
        existing = {s["name"] for s in db.get_screener_saved()}
    except Exception as e:
        logger.warning(f"seed_default_screeners: could not read existing screeners: {e}")
        return

    for preset in DEFAULT_SCREENERS:
        if preset["name"] in existing:
            continue
        try:
            db.save_screener(preset["name"], preset["spec"])
        except Exception as e:
            logger.warning(f"seed_default_screeners: failed to seed {preset['name']}: {e}")

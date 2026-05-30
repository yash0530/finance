"""
seed_themes.py — idempotent default theme/ticker seed.

Called once on boot from db.init_db(). Uses INSERT OR IGNORE semantics via the
db CRUD helpers so re-running never duplicates or overwrites user edits: a theme
or ticker that already exists is left untouched.

The default pack is AI/semis-pilled per the v3 PRD. Editable in Settings.
"""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


DEFAULT_THEMES: List[Dict] = [
    {
        "slug": "ai-infra",
        "name": "AI Infra / Compute",
        "description": "Compute, accelerators, and the hyperscale buildout.",
        "tickers": ["NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM", "MRVL", "SMCI", "DELL", "ORCL", "MSFT"],
    },
    {
        "slug": "hbm-memory",
        "name": "HBM / Memory & Equipment",
        "description": "High-bandwidth memory and semicap equipment.",
        "tickers": ["MU", "WDC", "STX", "LRCX", "AMAT", "KLAC"],
    },
    {
        "slug": "dc-power",
        "name": "Datacenter Power & Energy",
        "description": "Power, cooling, and generation for datacenters.",
        "tickers": ["VRT", "ETN", "GEV", "CEG", "VST", "NRG", "TLN", "OKLO", "SMR", "BWXT"],
    },
    {
        "slug": "networking-optics",
        "name": "Networking & Optics",
        "description": "Switching, optical interconnect, and transceivers.",
        "tickers": ["ANET", "CIEN", "COHR", "LITE", "FN", "INFN", "AAOI", "IPGP"],
    },
    {
        "slug": "drones-defense",
        "name": "Drones & Defense",
        "description": "Autonomous systems, primes, and defense tech.",
        "tickers": ["KTOS", "AVAV", "RKLB", "PLTR", "LMT", "NOC", "RTX", "LDOS", "BAH"],
    },
    {
        "slug": "robotics",
        "name": "Robotics & Autonomy",
        "description": "Industrial robotics, surgical, and autonomy.",
        "tickers": ["TSLA", "ABB", "ISRG", "ROK", "IRBT", "MBLY", "SYM", "FANUY"],
    },
]


def seed_default_themes() -> None:
    """Insert default themes and tickers if they don't already exist.

    Idempotent: existing themes (matched by slug) are left untouched and their
    tickers are not re-seeded, so the user's edits survive every boot.
    """
    import db

    try:
        existing = {t["slug"] for t in db.get_themes()}
    except Exception as e:
        logger.warning(f"seed_default_themes: could not read existing themes: {e}")
        return

    for theme in DEFAULT_THEMES:
        if theme["slug"] in existing:
            continue
        try:
            db.upsert_theme(theme["slug"], theme["name"], theme["description"])
            for ticker in theme["tickers"]:
                db.add_theme_ticker(theme["slug"], ticker)
        except Exception as e:
            logger.warning(f"seed_default_themes: failed to seed {theme['slug']}: {e}")

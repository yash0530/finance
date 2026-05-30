"""
themes_service.py — theme pack queries used by Terminal panels and Stock View.

Thin orchestration over db theme CRUD. Resolves theme membership and the union
of tickers a scan should cover. No LLM, no network — pure DB reads.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import db


def list_themes() -> List[Dict]:
    return db.get_themes()


def get_theme_detail(slug: str) -> Optional[Dict]:
    theme = db.get_theme(slug)
    if not theme:
        return None
    theme["tickers"] = db.get_theme_tickers(slug)
    return theme


def tickers_for_theme(slug: str) -> List[str]:
    return [t["ticker"] for t in db.get_theme_tickers(slug)]


def themes_for_ticker(ticker: str) -> List[Dict]:
    return db.get_themes_for_ticker(ticker)


def all_theme_tickers() -> List[str]:
    return db.all_theme_tickers()


def scan_universe(extra: Optional[List[str]] = None) -> List[str]:
    """Union of every theme's tickers plus an optional extra list (e.g. watchlist)."""
    seen, out = set(), []
    for ticker in db.all_theme_tickers() + list(extra or []):
        u = ticker.upper().strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out

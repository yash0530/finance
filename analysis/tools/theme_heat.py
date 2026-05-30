"""
tools.theme_heat — per-theme intraday heat: median % move + leader/laggard.

For each theme pack, batches quotes for its constituents (reusing movers'
fetch_quotes) and computes the median percent move plus the strongest and
weakest names. Cached 15 minutes.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


def _theme_packs() -> List[Dict[str, Any]]:
    import themes_service
    packs = []
    for theme in themes_service.list_themes():
        packs.append({
            "slug": theme["slug"],
            "name": theme["name"],
            "tickers": themes_service.tickers_for_theme(theme["slug"]),
        })
    return packs


class ThemeHeatTool(Tool):
    name = "theme_heat"
    description = (
        "Per-theme intraday heat: median percent move across each theme pack's "
        "constituents, plus leader and laggard. Cached 15 minutes."
    )
    cache_ttl_seconds = 15 * 60
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, **kwargs) -> ToolResult:
        from tools.movers import fetch_quotes

        packs = _theme_packs()
        if not packs:
            return ToolResult(
                tool_name=self.name, data={"themes": []},
                sources=[], confidence="low",
                error="No themes defined",
            )

        all_tickers = sorted({t for p in packs for t in p["tickers"]})
        cache_key = ",".join(all_tickers)
        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="high", cached=True,
            )

        quotes = fetch_quotes(all_tickers)

        themes_out: List[Dict[str, Any]] = []
        for pack in packs:
            rows = [quotes[t] for t in pack["tickers"] if t in quotes]
            if not rows:
                themes_out.append({
                    "slug": pack["slug"], "name": pack["name"],
                    "median_change_pct": None, "resolved": 0,
                    "constituent_count": len(pack["tickers"]),
                    "leader": None, "laggard": None,
                })
                continue
            changes = [r["change_pct"] for r in rows]
            leader = max(rows, key=lambda r: r["change_pct"])
            laggard = min(rows, key=lambda r: r["change_pct"])
            themes_out.append({
                "slug": pack["slug"],
                "name": pack["name"],
                "median_change_pct": round(median(changes), 2),
                "resolved": len(rows),
                "constituent_count": len(pack["tickers"]),
                "leader": {"ticker": leader["ticker"], "change_pct": leader["change_pct"]},
                "laggard": {"ticker": laggard["ticker"], "change_pct": laggard["change_pct"]},
            })

        themes_out.sort(
            key=lambda t: (t["median_change_pct"] if t["median_change_pct"] is not None else -999),
            reverse=True,
        )

        data = {"themes": themes_out, "as_of": datetime.now().isoformat()}
        save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=False),
            confidence="high",
        )


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note = "yfinance fast_info via theme packs" + (" (cached)" if cached else "")
    return [Source(tool="theme_heat", field="themes", fetched_at=now, url=None, note=note)]


register(ThemeHeatTool())

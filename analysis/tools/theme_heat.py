"""
tools.theme_heat — per-theme intraday heat: median % move + leader/laggard.

For each theme pack, batches quotes for its constituents (reusing movers'
fetch_quotes) and computes the median percent move plus the strongest and
weakest names. Cached 15 minutes.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, get_tool_cache_stale, save_tool_cache


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


def _sp500_sector_packs() -> List[Dict[str, Any]]:
    """One pack per GICS sector, constituents from the S&P 500 snapshot cache."""
    from tools.sp500_lookup import sp500_by_sector
    packs = []
    for sector, tickers in sp500_by_sector().items():
        packs.append({
            "slug": "sp500:" + sector.lower().replace(" ", "-"),
            "name": sector,
            "tickers": tickers,
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
        return {
            "type": "object",
            "properties": {
                "universe": {
                    "type": "string",
                    "enum": ["themes", "sp500-sectors"],
                    "description": "Group by user theme packs (default) or by GICS sector across the S&P 500.",
                },
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, universe: str = "themes", **kwargs) -> ToolResult:
        from tools.quote_snapshot import QuoteSnapshotTool

        packs = _sp500_sector_packs() if universe == "sp500-sectors" else _theme_packs()
        if not packs:
            return ToolResult(
                tool_name=self.name, data={"themes": [], "universe": universe},
                sources=[], confidence="low",
                error="No S&P 500 snapshot available" if universe == "sp500-sectors" else "No themes defined",
            )

        all_tickers = sorted({t for p in packs for t in p["tickers"]})
        cache_key = f"{universe}|" + ",".join(all_tickers)
        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="high", cached=True,
            )

        quote_result = QuoteSnapshotTool().execute(tickers=all_tickers)
        quotes = quote_result.data.get("quotes", {})
        if not quotes:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned no theme constituents.")
            if stale:
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )

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

        resolved_total = sum(int(t.get("resolved") or 0) for t in themes_out)
        data = {
            "themes": themes_out,
            "universe": universe,
            "resolved_count": resolved_total,
            "requested_count": len(all_tickers),
            "as_of": datetime.now().isoformat(),
        }
        if quote_result.data.get("confidence_warning"):
            data["confidence_warning"] = quote_result.data["confidence_warning"]
        if quote_result.data.get("stale"):
            data["stale"] = True
            data["cache_status"] = "stale"
            data["stale_reason"] = quote_result.data.get("stale_reason")

        if resolved_total < len(all_tickers) * 0.5:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned sparse theme data.")
            if stale and int(stale.get("resolved_count") or 0) > resolved_total:
                stale["live_resolved"] = resolved_total
                stale["live_requested_count"] = len(all_tickers)
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )
            data["cache_status"] = data.get("cache_status") or "live_sparse"
            data["confidence_warning"] = data.get("confidence_warning") or "Sparse market data detected. Theme heat may be incomplete."
            return ToolResult(
                tool_name=self.name, data=data,
                sources=_build_sources(data, cached=False),
                confidence="low",
            )

        if not data.get("stale"):
            save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=quote_result.cached),
            confidence="low" if quote_result.confidence == "low" or data.get("stale") else "high",
            cached=quote_result.cached,
        )


def _stale_payload(tool_name: str, cache_key: str, reason: str) -> Optional[Dict[str, Any]]:
    stale = get_tool_cache_stale(tool_name, cache_key)
    if not stale:
        return None
    stale = dict(stale)
    stale["stale"] = True
    stale["cache_status"] = "stale"
    stale["confidence_warning"] = f"{reason} Showing last successful snapshot."
    stale["stale_reason"] = reason
    return stale


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    if data.get("stale"):
        note = "yfinance fast_info via theme packs (stale cache)"
    else:
        note = "yfinance fast_info via theme packs" + (" (cached)" if cached else "")
    return [Source(tool="theme_heat", field="themes", fetched_at=now, url=None, note=note)]


register(ThemeHeatTool())

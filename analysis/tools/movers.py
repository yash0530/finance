"""
tools.movers — batched daily quotes + top movers across a ticker universe.

Reads last price / previous close / volume from yfinance fast_info (no full
history download), in parallel. Returns the top gainers and losers by intraday
percentage move. Cached 15 minutes.

The universe is resolved by the caller (the /api/terminal/movers endpoint);
the tool itself just takes an explicit ticker list. DEFAULT_UNIVERSE seeds the
Terminal before the user has built a watchlist or theme packs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, get_tool_cache_stale, save_tool_cache
from tools.quote_snapshot import QuoteSnapshotTool, fetch_quotes


DEFAULT_UNIVERSE: List[str] = [
    "NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM",
    "MRVL", "SMCI", "DELL", "ORCL", "MSFT",
]


class MoversTool(Tool):
    name = "movers"
    description = (
        "Top gainers and losers by intraday percent move across a ticker "
        "universe, via batched yfinance fast_info quotes. Cached 15 minutes."
    )
    cache_ttl_seconds = 15 * 60
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ticker universe to scan",
                },
                "top_n": {"type": "integer", "description": "Count per side (default 10)"},
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, tickers: Optional[List[str]] = None, top_n: int = 10, **kwargs) -> ToolResult:
        universe = [t.upper().strip() for t in (tickers or DEFAULT_UNIVERSE)]
        cache_key = ",".join(sorted(set(universe))) + f"|{top_n}"

        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="high", cached=True,
            )

        quote_result = QuoteSnapshotTool().execute(tickers=universe)
        quotes = quote_result.data.get("quotes", {})
        ranked = sorted(quotes.values(), key=lambda q: q["change_pct"], reverse=True)

        universe_size = len(universe)
        resolved = len(ranked)

        data: Dict[str, Any] = {
            "universe_size": universe_size,
            "resolved": resolved,
            "resolved_count": resolved,
            "requested_count": universe_size,
            "gainers": ranked[:top_n],
            "losers": list(reversed(ranked[-top_n:])) if ranked else [],
            "as_of": datetime.now().isoformat(),
        }
        if quote_result.data.get("confidence_warning"):
            data["confidence_warning"] = quote_result.data["confidence_warning"]
        if quote_result.data.get("stale"):
            data["stale"] = True
            data["cache_status"] = "stale"
            data["stale_reason"] = quote_result.data.get("stale_reason")

        if not ranked:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned no resolvable tickers.")
            if stale:
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )
            return ToolResult(
                tool_name=self.name, data=data,
                sources=[], confidence="low",
                error="No quotes resolved for universe",
            )

        confidence = "low" if quote_result.confidence == "low" or data.get("stale") else "high"
        if resolved < universe_size * 0.5:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned sparse data.")
            if stale and int(stale.get("resolved") or 0) > resolved:
                stale["live_resolved"] = resolved
                stale["live_universe_size"] = universe_size
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )
            data["confidence_warning"] = data.get("confidence_warning") or "Sparse market data detected. More than 50% of tickers in the scan universe failed to resolve."
            data["cache_status"] = "live_sparse"
            return ToolResult(
                tool_name=self.name, data=data,
                sources=_build_sources(data, cached=False),
                confidence=confidence,
            )

        if not data.get("stale"):
            save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=quote_result.cached),
            confidence=confidence,
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
        note = "yfinance fast_info (stale cache)"
    else:
        note = "yfinance fast_info" + (" (cached)" if cached else "")
    return [Source(
        tool="movers", field="gainers/losers",
        fetched_at=now, url=None, note=note,
    )]


register(MoversTool())

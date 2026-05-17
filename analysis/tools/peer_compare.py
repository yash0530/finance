"""
tools.peer_compare — wraps research_engine.get_peer_valuation as a v2 Tool.

Returns sector-average valuation multiples (P/E, P/S, P/B) used to contextualize
a ticker's own multiples. Cached for 24h (sector averages move slowly).
"""

from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


class PeerCompareTool(Tool):
    name = "peer_compare"
    description = (
        "Sector-average valuation multiples (P/E, P/S, P/B) for benchmarking "
        "a ticker against its sector. Requires the sector string from the "
        "fundamentals tool. Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "sector": {
                    "type": "string",
                    "description": "Sector name (e.g. 'Technology'). Comes from fundamentals.sector.",
                },
            },
            "required": ["ticker", "sector"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, sector: str = "", **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        sector = (sector or "").strip()
        cache_key = f"{ticker}:{sector}"

        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="medium",
                cached=True,
            )

        from research_engine import get_peer_valuation
        data = get_peer_valuation(ticker, sector)

        if not isinstance(data, dict) or not data:
            return ToolResult(
                tool_name=self.name, data={},
                error="No peer valuation data returned", confidence="low",
            )

        save_tool_cache(self.name, cache_key, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(data, cached=False),
            confidence="medium",  # sector averages are coarse
        )


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note_suffix = " (cached)" if cached else ""
    sector = data.get("sector", "")
    sources: List[Source] = []
    for field_name in ("average_pe", "average_ps", "average_pb"):
        if data.get(field_name) is not None:
            sources.append(Source(
                tool="peer_compare",
                field=field_name,
                fetched_at=now,
                url=None,
                note=f"sector benchmark ({sector}){note_suffix}",
            ))
    return sources


register(PeerCompareTool())

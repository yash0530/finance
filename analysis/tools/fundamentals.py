"""
tools.fundamentals — wraps research_engine.fetch_fundamentals as a v2 Tool.

Pulls baseline financial metrics from yfinance: market cap, valuation multiples,
margins, balance sheet ratios, analyst target. Cached for 4 hours.
"""

from datetime import datetime
from typing import Any, Dict

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


class FundamentalsTool(Tool):
    name = "fundamentals"
    description = (
        "Baseline financial snapshot for a US-listed ticker via yfinance: "
        "market cap, P/E (forward + trailing), revenue and growth, margins, "
        "balance sheet ratios, 52-week range, analyst target. Cached 4h."
    )
    cache_ttl_seconds = 4 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0  # yfinance is free

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()

        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached, cached=True),
                confidence="high",
                cached=True,
            )

        from research_engine import fetch_fundamentals
        data = fetch_fundamentals(ticker)

        if data.get("error"):
            return ToolResult(
                tool_name=self.name, data={},
                error=data["error"], confidence="low",
            )

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence="high" if data.get("current_price") else "medium",
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> list:
    now = datetime.now().isoformat()
    note = "yfinance cache" if cached else "yfinance .info"
    sources = []
    # One source per top-level numeric field that downstream agents are likely to cite
    for field_name in (
        "current_price", "market_cap", "forward_pe", "trailing_pe",
        "revenue", "net_income", "profit_margin", "revenue_growth",
        "week_52_high", "week_52_low", "analyst_target",
    ):
        if data.get(field_name) is not None:
            sources.append(Source(
                tool="fundamentals", field=field_name,
                fetched_at=now,
                url=f"https://finance.yahoo.com/quote/{ticker}",
                note=note,
            ))
    return sources


register(FundamentalsTool())

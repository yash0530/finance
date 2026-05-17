"""
tools.financial_trends — wraps research_engine.fetch_financial_trends as a v2 Tool.

Pulls 8-12 quarters of income / balance sheet / cash-flow data from yfinance
and computes trajectory signals (margin expansion, revenue acceleration,
earnings quality, etc.). Cached for 4 hours.
"""

from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


class FinancialTrendsTool(Tool):
    name = "financial_trends"
    description = (
        "Multi-quarter financial trajectory for a US-listed ticker via yfinance: "
        "8-12 quarters of revenue, margins, FCF, ROE, debt; plus computed "
        "trend signals (expanding/contracting, acceleration, earnings quality). "
        "Cached 4h."
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

        from research_engine import fetch_financial_trends
        data = fetch_financial_trends(ticker)

        if data.get("error"):
            return ToolResult(
                tool_name=self.name, data={},
                error=data["error"], confidence="low",
            )

        save_tool_cache(self.name, ticker, data)

        quarter_count = data.get("quarter_count", 0)
        confidence = "high" if quarter_count >= 6 else ("medium" if quarter_count >= 2 else "low")

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence=confidence,
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note_suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    url = f"https://finance.yahoo.com/quote/{ticker}/financials"
    for q in data.get("quarters", []) or []:
        date = q.get("date") or q.get("quarter_label", "")
        if not date:
            continue
        sources.append(Source(
            tool="financial_trends",
            field=f"quarter:{date}",
            fetched_at=now,
            url=url,
            note=f"yfinance quarterly financials{note_suffix}",
        ))
    return sources


register(FinancialTrendsTool())

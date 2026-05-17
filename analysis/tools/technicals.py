"""
tools.technicals — wraps research_engine.fetch_technicals as a v2 Tool.

Computes RSI, MACD, Bollinger Bands, 50/200-day moving averages, golden/death
cross, pattern detection, and 1y return / volatility from yfinance daily price
history. Cached for 1h (price data is volatile).
"""

from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


class TechnicalsTool(Tool):
    name = "technicals"
    description = (
        "Technical indicators for a US-listed ticker: RSI(14), MACD(12,26,9), "
        "Bollinger Bands, 50/200-day MAs, golden/death cross, detected chart "
        "patterns, 1y return and annualized volatility. Cached 1h."
    )
    cache_ttl_seconds = 1 * 3600
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

        from research_engine import fetch_technicals
        data = fetch_technicals(ticker)

        if data.get("error"):
            return ToolResult(
                tool_name=self.name, data={},
                error=data["error"], confidence="low",
            )

        save_tool_cache(self.name, ticker, data)

        data_points = data.get("data_points", 0)
        confidence = "high" if data_points >= 200 else ("medium" if data_points >= 50 else "low")

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence=confidence,
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note_suffix = " (cached)" if cached else ""
    url = f"https://finance.yahoo.com/quote/{ticker}/history"
    sources: List[Source] = []

    # One source per top-level indicator that the LLM is likely to cite
    for indicator in ("rsi", "macd", "ma_50", "ma_200"):
        if data.get(indicator) is not None:
            sources.append(Source(
                tool="technicals",
                field=indicator,
                fetched_at=now,
                url=url,
                note=f"yfinance daily history → {indicator}{note_suffix}",
            ))

    # Patterns: one source per detected pattern (with confidence note)
    for pat in data.get("patterns", []) or []:
        pat_type = pat.get("type", "pattern") if isinstance(pat, dict) else str(pat)
        pat_conf = pat.get("confidence") if isinstance(pat, dict) else None
        note = f"detected chart pattern: {pat_type}"
        if pat_conf is not None:
            note += f" (confidence={pat_conf})"
        note += note_suffix
        sources.append(Source(
            tool="technicals",
            field=f"patterns:{pat_type}",
            fetched_at=now,
            url=url,
            note=note,
        ))

    return sources


register(TechnicalsTool())

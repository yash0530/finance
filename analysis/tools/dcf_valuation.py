"""
tools.dcf_valuation — wraps research_engine.compute_intrinsic_value as a v2 Tool.

Runs a 3-scenario (bear/base/bull) DCF using TTM FCF, an inferred growth rate
from recent revenue growth, and standard WACC/terminal assumptions. Needs
`fundamentals` and `trends` inputs. If they are not supplied, this tool fetches
them itself via the registered `fundamentals` and `financial_trends` tools.

Cached for 4h.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register, get_tool
from db import get_tool_cache, save_tool_cache


class DCFValuationTool(Tool):
    name = "dcf_valuation"
    description = (
        "Discounted Cash Flow intrinsic value for a US-listed ticker. Produces "
        "bear/base/bull per-share values, a verdict (Undervalued/Fair/Overvalued), "
        "and a margin-of-safety. Will fetch fundamentals+trends internally if "
        "not provided. Cached 4h."
    )
    cache_ttl_seconds = 4 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "fundamentals_data": {
                    "type": "object",
                    "description": "Optional pre-fetched fundamentals dict from the fundamentals tool.",
                },
                "trends_data": {
                    "type": "object",
                    "description": "Optional pre-fetched financial_trends dict.",
                },
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0  # yfinance + arithmetic only

    def _execute(
        self,
        ticker: str,
        fundamentals_data: Optional[Dict] = None,
        trends_data: Optional[Dict] = None,
        **kwargs,
    ) -> ToolResult:
        ticker = ticker.upper().strip()

        # Cache key is just the ticker — inputs are deterministic given the
        # other tools' caches (also 4h).
        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached, cached=True),
                confidence="high" if not cached.get("error") else "low",
                cached=True,
            )

        # Fetch deps internally if not provided
        if fundamentals_data is None:
            fundamentals_data = _invoke_tool("fundamentals", ticker)
        if trends_data is None:
            trends_data = _invoke_tool("financial_trends", ticker)

        fundamentals_data = fundamentals_data or {}
        trends_data = trends_data or {}

        from research_engine import compute_intrinsic_value
        data = compute_intrinsic_value(ticker, fundamentals_data, trends_data)

        if data.get("error"):
            return ToolResult(
                tool_name=self.name, data={},
                error=data["error"], confidence="low",
            )

        if data.get("skipped"):
            # ETF or otherwise N/A — still a valid (non-error) result.
            return ToolResult(
                tool_name=self.name,
                data=data,
                sources=[],
                confidence="medium",
            )

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence="medium",  # DCF outputs are model-sensitive
        )


def _invoke_tool(tool_name: str, ticker: str) -> Dict:
    """Look up a registered tool and execute it; return data dict or empty."""
    tool = get_tool(tool_name)
    if tool is None:
        return {}
    res = tool.execute(ticker=ticker)
    return res.data if res.is_ok() else {}


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note_suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    url = f"https://finance.yahoo.com/quote/{ticker}/cash-flow"

    for field_name in ("base_case", "bull_case", "bear_case", "margin_of_safety_pct", "verdict"):
        if data.get(field_name) is not None:
            sources.append(Source(
                tool="dcf_valuation",
                field=field_name,
                fetched_at=now,
                url=url,
                note=f"3-scenario DCF; inputs from fundamentals + financial_trends{note_suffix}",
            ))
    return sources


register(DCFValuationTool())

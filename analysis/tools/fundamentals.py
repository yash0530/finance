"""
tools.fundamentals — wraps research_engine.fetch_fundamentals as a v2 Tool.

Pulls baseline financial metrics from yfinance: market cap, valuation multiples,
margins, balance sheet ratios, analyst target. Cached for 4 hours.
"""

from datetime import datetime
from typing import Any, Dict

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


def _raw_value(item: Any) -> Any:
    if isinstance(item, dict):
        reported = item.get("reportedValue")
        if isinstance(reported, dict):
            return reported.get("raw")
        return item.get("raw")
    return item


def _latest_series_value(result: Dict[str, Any], key: str) -> Any:
    values = result.get(key) or []
    if not values:
        return None
    return _raw_value(values[-1])


def _fetch_yahoo_fundamentals_fallback(ticker: str) -> Dict[str, Any]:
    """Non-yfinance fallback for the Stock View when .info is rate-limited."""
    import requests
    import time

    headers = {"User-Agent": "Mozilla/5.0"}
    data: Dict[str, Any] = {}

    chart_res = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        params={"range": "1y", "interval": "1d"},
        headers=headers,
        timeout=12,
    )
    chart_res.raise_for_status()
    chart = chart_res.json()
    meta = ((((chart.get("chart") or {}).get("result") or [{}])[0]) or {}).get("meta") or {}
    data.update({
        "ticker": ticker,
        "company_name": meta.get("longName") or meta.get("shortName"),
        "current_price": meta.get("regularMarketPrice"),
        "price": meta.get("regularMarketPrice"),
        "market_cap": meta.get("marketCap"),
        "week_52_high": meta.get("fiftyTwoWeekHigh"),
        "week_52_low": meta.get("fiftyTwoWeekLow"),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
    })

    period2 = int(time.time())
    period1 = period2 - (1000 * 24 * 60 * 60)
    types = ",".join([
        "trailingPeRatio",
        "trailingForwardPeRatio",
        "trailingTotalRevenue",
        "trailingNetIncome",
        "annualTotalRevenue",
    ])
    ts_res = requests.get(
        f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{ticker}",
        params={"symbol": ticker, "type": types, "period1": period1, "period2": period2},
        headers=headers,
        timeout=12,
    )
    ts_res.raise_for_status()
    ts_payload = ts_res.json()
    for result in ((ts_payload.get("timeseries") or {}).get("result") or []):
        result_type = ((result.get("meta") or {}).get("type") or [None])[0]
        if result_type == "trailingPeRatio":
            data["trailing_pe"] = _latest_series_value(result, "trailingPeRatio")
        elif result_type == "trailingForwardPeRatio":
            data["forward_pe"] = _latest_series_value(result, "trailingForwardPeRatio")
        elif result_type == "trailingTotalRevenue":
            revenue = _latest_series_value(result, "trailingTotalRevenue")
            data["revenue"] = revenue
            data["total_revenue"] = revenue
        elif result_type == "trailingNetIncome":
            data["net_income"] = _latest_series_value(result, "trailingNetIncome")
        elif result_type == "annualTotalRevenue":
            annual = result.get("annualTotalRevenue") or []
            if len(annual) >= 2:
                latest = _raw_value(annual[-1])
                previous = _raw_value(annual[-2])
                if latest is not None and previous:
                    data["revenue_growth"] = (float(latest) - float(previous)) / float(previous)

    if data.get("revenue") and data.get("net_income") is not None:
        data["profit_margin"] = float(data["net_income"]) / float(data["revenue"])

    return {k: v for k, v in data.items() if v is not None}


def _merge_non_null(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value is not None:
            merged[key] = value
    return merged


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
            if any(cached.get(field) is None for field in ("forward_pe", "trailing_pe", "revenue", "profit_margin", "week_52_high", "week_52_low")):
                try:
                    fallback = _fetch_yahoo_fundamentals_fallback(ticker)
                    cached = _merge_non_null(cached, fallback)
                    save_tool_cache(self.name, ticker, cached)
                except Exception:
                    pass
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
            try:
                fallback = _fetch_yahoo_fundamentals_fallback(ticker)
            except Exception:
                fallback = {}
            if not fallback:
                return ToolResult(
                    tool_name=self.name, data={},
                    error=data["error"], confidence="low",
                )
            save_tool_cache(self.name, ticker, fallback)
            return ToolResult(
                tool_name=self.name,
                data=fallback,
                error=f"yfinance unavailable; used Yahoo fundamentals fallback: {data['error']}",
                sources=_build_sources(ticker, fallback, cached=False, fallback=True),
                confidence="medium",
            )

        try:
            fallback = _fetch_yahoo_fundamentals_fallback(ticker)
            data = _merge_non_null(fallback, data)
        except Exception:
            pass

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence="high" if data.get("current_price") else "medium",
        )


def _build_sources(ticker: str, data: Dict, cached: bool, fallback: bool = False) -> list:
    now = datetime.now().isoformat()
    note = "yfinance cache" if cached else "Yahoo Finance chart/timeseries fallback" if fallback else "yfinance .info"
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

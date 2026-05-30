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

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


DEFAULT_UNIVERSE: List[str] = [
    "NVDA", "AMD", "AVGO", "TSM", "ASML", "ARM",
    "MRVL", "SMCI", "DELL", "ORCL", "MSFT",
]


def _fi_get(fi: Any, *names: str) -> Optional[float]:
    """Read a field from a yfinance fast_info object across naming variants."""
    for name in names:
        try:
            v = getattr(fi, name)
            if v is not None:
                return float(v)
        except (AttributeError, TypeError, ValueError):
            pass
        try:
            v = fi[name]
            if v is not None:
                return float(v)
        except (KeyError, TypeError, ValueError):
            pass
    return None


def fetch_quotes(tickers: List[str], max_workers: int = 10) -> Dict[str, Dict[str, Any]]:
    """Return {ticker: {price, previous_close, change_pct, volume, market_cap}}.

    Tickers that fail to resolve are omitted. Network is per-ticker fast_info.
    """
    import yfinance as yf

    def _one(ticker: str):
        try:
            fi = yf.Ticker(ticker).fast_info
            price = _fi_get(fi, "last_price", "lastPrice")
            prev = _fi_get(fi, "previous_close", "previousClose", "regularMarketPreviousClose")
            volume = _fi_get(fi, "last_volume", "lastVolume", "regularMarketVolume")
            market_cap = _fi_get(fi, "market_cap", "marketCap")
            if price is None or prev is None or prev == 0:
                return ticker, None
            return ticker, {
                "ticker": ticker,
                "price": round(price, 4),
                "previous_close": round(prev, 4),
                "change_pct": round((price - prev) / prev * 100, 2),
                "volume": int(volume) if volume is not None else None,
                "market_cap": market_cap,
            }
        except Exception:
            return ticker, None

    out: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for ticker, quote in pool.map(_one, [t.upper().strip() for t in tickers]):
            if quote is not None:
                out[ticker] = quote
    return out


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

        quotes = fetch_quotes(universe)
        ranked = sorted(quotes.values(), key=lambda q: q["change_pct"], reverse=True)

        data: Dict[str, Any] = {
            "universe_size": len(universe),
            "resolved": len(ranked),
            "gainers": ranked[:top_n],
            "losers": list(reversed(ranked[-top_n:])) if ranked else [],
            "as_of": datetime.now().isoformat(),
        }
        if not ranked:
            return ToolResult(
                tool_name=self.name, data=data,
                sources=[], confidence="low",
                error="No quotes resolved for universe",
            )

        save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=False),
            confidence="high",
        )


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note = "yfinance fast_info" + (" (cached)" if cached else "")
    return [Source(
        tool="movers", field="gainers/losers",
        fetched_at=now, url=None, note=note,
    )]


register(MoversTool())

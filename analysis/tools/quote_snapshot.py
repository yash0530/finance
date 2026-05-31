"""
tools.quote_snapshot — shared quote map for Daily Scan surfaces.

Fetches current price, previous close, volume, and market cap for a ticker
universe. This is the quote spine used by movers, theme heat, watchlist
enrichment, and the terminal snapshot endpoint so a morning scan does not make
duplicate provider calls for the same symbols. Cached 5 minutes with stale-good
fallback when the live provider fails.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, get_tool_cache_stale, save_tool_cache


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


def _normalize_universe(tickers: List[str]) -> List[str]:
    seen, out = set(), []
    for ticker in tickers:
        t = str(ticker or "").upper().strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def fetch_quotes_live(tickers: List[str], max_workers: int = 10) -> Dict[str, Dict[str, Any]]:
    """Return live quotes only. Tickers that fail to resolve are omitted."""
    import yfinance as yf

    universe = _normalize_universe(tickers)
    if not universe:
        return {}

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
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(universe)))) as pool:
        for ticker, quote in pool.map(_one, universe):
            if quote is not None:
                out[ticker] = quote
    return out


def fetch_quotes(tickers: List[str], max_workers: int = 10) -> Dict[str, Dict[str, Any]]:
    """Return cached/live quotes for compatibility with existing callers."""
    return QuoteSnapshotTool().execute(tickers=tickers, max_workers=max_workers).data.get("quotes", {})


class QuoteSnapshotTool(Tool):
    name = "quote_snapshot"
    description = (
        "Shared quote map for a ticker universe via yfinance fast_info. "
        "Cached 5 minutes with stale fallback."
    )
    cache_ttl_seconds = 5 * 60
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ticker universe to quote",
                },
                "max_workers": {"type": "integer", "description": "Concurrent quote fetches"},
            },
            "required": ["tickers"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(
        self,
        tickers: Optional[List[str]] = None,
        max_workers: int = 10,
        **kwargs,
    ) -> ToolResult:
        universe = _normalize_universe(tickers or [])
        cache_key = ",".join(universe)
        if not universe:
            return ToolResult(
                tool_name=self.name,
                data={
                    "quotes": {},
                    "requested_count": 0,
                    "resolved_count": 0,
                    "unresolved": [],
                    "as_of": datetime.now().isoformat(),
                },
                sources=[],
                confidence="low",
                error="No ticker(s) provided",
            )

        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="high", cached=True,
            )

        quotes = fetch_quotes_live(universe, max_workers=max_workers)
        resolved = len(quotes)
        unresolved = [t for t in universe if t not in quotes]
        data: Dict[str, Any] = {
            "quotes": quotes,
            "requested_count": len(universe),
            "resolved_count": resolved,
            "unresolved": unresolved,
            "as_of": datetime.now().isoformat(),
            "cache_status": "live",
        }

        if resolved == 0:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned no resolvable tickers.")
            if stale:
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )
            return ToolResult(
                tool_name=self.name, data=data,
                sources=[],
                confidence="low",
                error="No quotes resolved for universe",
            )

        if resolved < len(universe) * 0.5:
            stale = _stale_payload(self.name, cache_key, "Live quote provider returned sparse data.")
            if stale and int(stale.get("resolved_count") or 0) > resolved:
                stale["live_resolved_count"] = resolved
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(stale, cached=True),
                    confidence="low", cached=True,
                )
            data["cache_status"] = "live_sparse"
            data["confidence_warning"] = "Sparse market data detected. More than 50% of tickers failed to resolve."
            return ToolResult(
                tool_name=self.name, data=data,
                sources=_build_sources(data, cached=False),
                confidence="low",
            )

        save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(data, cached=False),
            confidence="high",
        )


def _stale_payload(tool_name: str, cache_key: str, reason: str) -> Optional[Dict[str, Any]]:
    stale = get_tool_cache_stale(tool_name, cache_key)
    if not stale:
        return None
    stale = dict(stale)
    stale["stale"] = True
    stale["cache_status"] = "stale"
    stale["confidence_warning"] = f"{reason} Showing last successful quote snapshot."
    stale["stale_reason"] = reason
    return stale


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    if data.get("stale"):
        note = "yfinance fast_info (stale quote snapshot)"
    else:
        note = "yfinance fast_info quote snapshot" + (" (cached)" if cached else "")
    return [Source(tool="quote_snapshot", field="quotes", fetched_at=now, url=None, note=note)]


register(QuoteSnapshotTool())

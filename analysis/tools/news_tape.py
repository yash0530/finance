"""
tools.news_tape — recent news headlines for a ticker or a set of tickers.

Primary source is Finnhub company-news (free tier). When no FINNHUB_API_KEY is
present, falls back to yfinance .news so the News Tape still populates on the
fully-free tier. Headlines are merged, de-duplicated, and sorted newest-first.
Cached 15 minutes.

Polygon fallback (POLYGON_API_KEY) is a documented data-tier upgrade; it is
gated inside _execute and absent here on the free tier.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


def _fetch_ticker_news(ticker: str, limit: int) -> List[Dict[str, Any]]:
    from sentiment_service import get_finnhub_news, get_yfinance_news
    import os

    if os.environ.get("FINNHUB_API_KEY", "").strip():
        articles = get_finnhub_news(ticker, days_back=7)
        if articles:
            return [_normalize(a, ticker) for a in articles[:limit]]
    return [_normalize(a, ticker) for a in get_yfinance_news(ticker)[:limit]]


def _normalize(article: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "headline": article.get("headline", ""),
        "summary": article.get("summary", ""),
        "url": article.get("url", ""),
        "source": article.get("source", ""),
        "published_at": article.get("published_at", ""),
    }


class NewsTapeTool(Tool):
    name = "news_tape"
    description = (
        "Recent news headlines for one or more tickers via Finnhub company-news "
        "(yfinance fallback when no key). Merged, de-duplicated, newest-first. "
        "Cached 15 minutes."
    )
    cache_ttl_seconds = 15 * 60
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Single ticker"},
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple tickers (overrides ticker)",
                },
                "limit": {"type": "integer", "description": "Max headlines (default 50)"},
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(
        self,
        ticker: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 50,
        **kwargs,
    ) -> ToolResult:
        universe = [t.upper().strip() for t in (tickers or ([ticker] if ticker else []))]
        if not universe:
            return ToolResult(
                tool_name=self.name, data={"items": []},
                sources=[], confidence="low",
                error="No ticker(s) provided",
            )

        cache_key = ",".join(sorted(set(universe))) + f"|{limit}"
        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence="medium", cached=True,
            )

        per_ticker = max(5, limit // max(1, len(universe)))
        collected: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(8, len(universe))) as pool:
            futures = [pool.submit(_fetch_ticker_news, t, per_ticker) for t in universe]
            for f in futures:
                try:
                    collected.extend(f.result())
                except Exception:
                    continue

        seen: set = set()
        deduped: List[Dict[str, Any]] = []
        for item in collected:
            key = (item.get("headline", "").strip().lower(), item.get("url", ""))
            if not item.get("headline") or key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        deduped.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        deduped = deduped[:limit]

        data = {
            "items": deduped,
            "count": len(deduped),
            "as_of": datetime.now().isoformat(),
        }
        save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=False),
            confidence="medium" if deduped else "low",
        )


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note = "Finnhub company-news / yfinance" + (" (cached)" if cached else "")
    return [Source(
        tool="news_tape", field="items",
        fetched_at=now, url=None, note=note,
    )]


register(NewsTapeTool())

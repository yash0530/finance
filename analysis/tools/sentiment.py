"""
tools.sentiment — wraps sentiment_service.get_composite_sentiment as a v2 Tool.

Smart-weighted composite of professional news (Finnhub), analyst ratings,
Reddit sentiment, and yfinance news fallback. Score is 0-10 with label
'bullish' / 'neutral' / 'bearish'.

NOT cached at the v2 layer (sentiment is time-sensitive; the underlying
service already uses ~1h in-memory caches per source).
"""

from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register


class SentimentTool(Tool):
    name = "sentiment"
    description = (
        "Composite sentiment score (0-10) for a US-listed ticker, weighting "
        "professional news, analyst consensus, and Reddit chatter. Includes "
        "top headlines and analyst breakdown. Not cached at the tool layer."
    )
    cache_ttl_seconds = 0       # time-sensitive
    requires_llm = True         # news headlines are scored by the LLM

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        # One small LLM call for headline scoring (a few hundred tokens).
        return 0.01

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()

        from sentiment_service import get_composite_sentiment
        try:
            data = get_composite_sentiment(ticker)
        except Exception as e:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"{type(e).__name__}: {e}", confidence="low",
            )

        if not isinstance(data, dict) or not data:
            return ToolResult(
                tool_name=self.name, data={},
                error="Empty sentiment result", confidence="low",
            )

        sources_used = data.get("sources_used", []) or []
        news_method = data.get("news_method", "none")

        # Confidence reflects how the headlines were scored. A keyword fallback
        # is worse than an LLM scoring; "none" means no headlines at all.
        if news_method == "llm" and len(sources_used) >= 2:
            confidence = "high"
        elif news_method == "llm" or len(sources_used) >= 2:
            confidence = "medium"
        elif sources_used:
            confidence = "low"
        else:
            confidence = "low"

        # Charge only when the LLM was actually invoked.
        actual_cost = self.estimate_cost() if news_method == "llm" else 0.0

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data),
            confidence=confidence,
            cost_usd=actual_cost,
        )


def _build_sources(ticker: str, data: Dict) -> List[Source]:
    now = datetime.now().isoformat()
    sources: List[Source] = []
    sources_used = data.get("sources_used", []) or []

    if "news" in sources_used:
        method = data.get("news_method", "none")
        n = data.get("news_headlines_scored", 0)
        if method == "llm":
            note = f"Finnhub / yfinance company news, LLM-scored ({n} headlines)"
        elif method == "keyword":
            note = f"Finnhub / yfinance company news, keyword-scored fallback ({n} headlines)"
        else:
            note = "Finnhub / yfinance company news (no scoring method applied)"
        sources.append(Source(
            tool="sentiment",
            field="news_score",
            fetched_at=now,
            url=None,
            note=note,
        ))

    # Analyst is always queried (may be empty if no Finnhub key)
    if data.get("analyst_count", 0) > 0 or "analyst" in sources_used:
        sources.append(Source(
            tool="sentiment",
            field="analyst_score",
            fetched_at=now,
            url=None,
            note=(
                f"Finnhub analyst consensus "
                f"({data.get('analyst_count', 0)} analysts, "
                f"rating={data.get('analyst_rating', 'N/A')})"
            ),
        ))

    if "reddit" in sources_used or data.get("reddit_mentions", 0) > 0:
        sources.append(Source(
            tool="sentiment",
            field="reddit_score",
            fetched_at=now,
            url=None,
            note=(
                f"Reddit (WSB / investing / stocks / options), "
                f"{data.get('reddit_mentions', 0)} mentions"
            ),
        ))

    # Top headlines, one per
    for headline in (data.get("top_headlines") or [])[:5]:
        sources.append(Source(
            tool="sentiment",
            field="headline",
            fetched_at=now,
            url=None,
            note=headline[:200],
        ))

    return sources


register(SentimentTool())

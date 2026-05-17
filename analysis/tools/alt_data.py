"""
tools.alt_data — lightweight alt-data signals.

v1: Google Trends interest score via pytrends.  If pytrends isn't installed
(most likely), the tool gracefully returns confidence="low" with a
"pytrends not installed" warning rather than failing.

Cached 24h.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


def _check_optional_import() -> Tuple[bool, Optional[Any]]:
    """Return (available, module).  Safe across pytrends import errors."""
    try:
        from pytrends.request import TrendReq  # type: ignore
        return True, TrendReq
    except Exception:
        return False, None


def _company_name(ticker: str) -> Optional[str]:
    """Best-effort lookup of long company name via yfinance.  None if it fails."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return (info.get("longName") or info.get("shortName") or None)
    except Exception:
        return None


def _trend_direction(delta: Optional[float]) -> Optional[str]:
    if delta is None:
        return None
    if delta > 10:
        return "rising"
    if delta < -10:
        return "falling"
    return "stable"


class AltDataTool(Tool):
    name = "alt_data"
    description = (
        "Lightweight alt-data signals: Google Trends interest (0-100) over 90d "
        "for the ticker and company name, plus 30d delta and rising/falling/"
        "stable classification. Gracefully degrades if pytrends isn't installed. "
        "Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
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
        return 0.0

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(ticker, cached, cached=True),
                confidence=cached.get("_confidence", "low"),
                cached=True,
            )

        warnings: List[str] = []
        available, TrendReq = _check_optional_import()

        if not available:
            warnings.append("pytrends not installed")
            data = {
                "ticker": ticker,
                "google_trends_score": None,
                "google_trends_30d_delta": None,
                "trend_direction": None,
                "available": False,
                "warnings": warnings,
                "_confidence": "low",
            }
            save_tool_cache(self.name, ticker, data)
            return ToolResult(
                tool_name=self.name, data=data,
                sources=_build_sources(ticker, data, cached=False),
                confidence="low",
            )

        score: Optional[int] = None
        delta: Optional[int] = None
        try:
            pytrends = TrendReq(hl="en-US", tz=360)
            terms = [ticker]
            company = _company_name(ticker)
            if company and company.lower() != ticker.lower():
                terms.append(company)
            # Build payload — past 90 days
            pytrends.build_payload(terms[:5], cat=0, timeframe="today 3-m", geo="", gprop="")
            df = pytrends.interest_over_time()
            if df is not None and not df.empty:
                # Combine across all chosen terms by row-wise max
                cols = [c for c in df.columns if c != "isPartial"]
                if cols:
                    series = df[cols].max(axis=1).astype(int)
                    score = int(series.iloc[-1])
                    # 30-day delta: ~last value vs value ~30 days ago
                    if len(series) >= 5:
                        n_ago = max(0, len(series) - 5)  # weekly cadence ~5 weeks
                        delta = int(series.iloc[-1]) - int(series.iloc[n_ago])
            else:
                warnings.append("pytrends returned no data")
        except Exception as e:
            warnings.append(f"pytrends error: {type(e).__name__}: {e}")

        direction = _trend_direction(float(delta) if delta is not None else None)

        data = {
            "ticker": ticker,
            "google_trends_score": score,
            "google_trends_30d_delta": delta,
            "trend_direction": direction,
            "available": score is not None,
            "warnings": warnings,
            "_confidence": "medium" if score is not None else "low",
        }
        save_tool_cache(self.name, ticker, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence=data["_confidence"],
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    if data.get("google_trends_score") is not None:
        sources.append(Source(
            tool="alt_data", field="google_trends_score",
            fetched_at=now,
            url=f"https://trends.google.com/trends/explore?q={ticker}",
            note=f"pytrends interest_over_time, 90d{suffix}",
        ))
    return sources


register(AltDataTool())

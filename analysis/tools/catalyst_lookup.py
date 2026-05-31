"""
tools.catalyst_lookup — upcoming catalysts for a ticker.

Company-specific catalysts (earnings, dividends) come from yfinance .calendar.
Market-wide catalysts (FOMC, CPI, NFP) come from a small hard-coded 2026
schedule.  Each catalyst is also persisted via db.upsert_catalyst() so a
catalyst calendar view can query them later.  Cached 6h.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache, upsert_catalyst

MARKET_WIDE_TICKER = "MARKET"


# ── Static market-wide calendar (2026) ───────────────────────────────────
# A representative, conservative set.  If you want to disable it for a run,
# just empty the list — the tool already handles that gracefully.
MARKET_WIDE_2026: List[Dict[str, str]] = [
    # FOMC announcement days (8 scheduled meetings/yr)
    {"type": "FOMC", "date": "2026-01-28", "description": "FOMC rate decision"},
    {"type": "FOMC", "date": "2026-03-18", "description": "FOMC rate decision + SEP"},
    {"type": "FOMC", "date": "2026-04-29", "description": "FOMC rate decision"},
    {"type": "FOMC", "date": "2026-06-17", "description": "FOMC rate decision + SEP"},
    {"type": "FOMC", "date": "2026-07-29", "description": "FOMC rate decision"},
    {"type": "FOMC", "date": "2026-09-16", "description": "FOMC rate decision + SEP"},
    {"type": "FOMC", "date": "2026-10-28", "description": "FOMC rate decision"},
    {"type": "FOMC", "date": "2026-12-16", "description": "FOMC rate decision + SEP"},
    # CPI prints (typically mid-month for prior month)
    {"type": "CPI", "date": "2026-05-13", "description": "April CPI release"},
    {"type": "CPI", "date": "2026-06-11", "description": "May CPI release"},
    {"type": "CPI", "date": "2026-07-15", "description": "June CPI release"},
    {"type": "CPI", "date": "2026-08-12", "description": "July CPI release"},
    {"type": "CPI", "date": "2026-09-10", "description": "August CPI release"},
    {"type": "CPI", "date": "2026-10-15", "description": "September CPI release"},
    {"type": "CPI", "date": "2026-11-12", "description": "October CPI release"},
    {"type": "CPI", "date": "2026-12-10", "description": "November CPI release"},
    # NFP releases (first Friday of month)
    {"type": "NFP", "date": "2026-06-05", "description": "May Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-07-03", "description": "June Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-08-07", "description": "July Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-09-04", "description": "August Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-10-02", "description": "September Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-11-06", "description": "October Non-Farm Payrolls"},
    {"type": "NFP", "date": "2026-12-04", "description": "November Non-Farm Payrolls"},
]


def _coerce_date(v: Any) -> Optional[str]:
    """Best-effort coercion of a yfinance calendar value to YYYY-MM-DD."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date().isoformat()
        except ValueError:
            return v[:10] if len(v) >= 10 else v
    if isinstance(v, (datetime, date)):
        return v.date().isoformat() if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, list) and v:
        return _coerce_date(v[0])
    # pandas.Timestamp etc.
    try:
        return v.date().isoformat()
    except Exception:
        try:
            return str(v)[:10]
        except Exception:
            return None


def _extract_calendar(cal: Any) -> Dict[str, Optional[str]]:
    """Pull earnings_date and dividend_date out of yfinance's varied calendar shapes."""
    out = {"earnings_date": None, "dividend_date": None}
    if cal is None:
        return out
    # yfinance returns either a dict or a DataFrame depending on version.
    if isinstance(cal, dict):
        ed = (cal.get("Earnings Date") or cal.get("earningsDate") or cal.get("Earnings Date "))
        dd = (cal.get("Ex-Dividend Date") or cal.get("Dividend Date") or cal.get("exDividendDate"))
        out["earnings_date"] = _coerce_date(ed)
        out["dividend_date"] = _coerce_date(dd)
        return out
    # DataFrame fallback
    try:
        if hasattr(cal, "loc"):
            for key in ("Earnings Date", "Earnings"):
                if key in cal.index:
                    out["earnings_date"] = _coerce_date(cal.loc[key].iloc[0])
                    break
            for key in ("Ex-Dividend Date", "Dividend Date"):
                if key in cal.index:
                    out["dividend_date"] = _coerce_date(cal.loc[key].iloc[0])
                    break
    except Exception:
        pass
    return out


def _future_only(events: List[Dict[str, str]]) -> List[Dict[str, str]]:
    today = date.today().isoformat()
    out = []
    for e in events:
        d = e.get("date")
        if d and d >= today:
            out.append(e)
    return out


class CatalystLookupTool(Tool):
    name = "catalyst_lookup"
    description = (
        "Upcoming catalysts for a ticker: earnings date and dividend date from "
        "yfinance, plus market-wide FOMC / CPI / NFP dates from a static "
        "calendar. Persists each event via db.upsert_catalyst. Cached 6h."
    )
    cache_ttl_seconds = 6 * 3600
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
                confidence=cached.get("_confidence", "medium"),
                cached=True,
            )

        warnings: List[str] = []

        # ── Company-specific via yfinance ─────────────────────────────
        earnings_date: Optional[str] = None
        dividend_date: Optional[str] = None
        try:
            import yfinance as yf
            cal = yf.Ticker(ticker).calendar
            extracted = _extract_calendar(cal)
            earnings_date = extracted["earnings_date"]
            dividend_date = extracted["dividend_date"]
        except Exception as e:
            warnings.append(f"yfinance calendar unavailable: {e}")

        company_specific: List[Dict[str, str]] = []
        if earnings_date:
            company_specific.append({
                "type": "earnings", "date": earnings_date,
                "description": f"{ticker} earnings",
            })
        if dividend_date:
            company_specific.append({
                "type": "dividend", "date": dividend_date,
                "description": f"{ticker} ex-dividend",
            })

        # ── Market-wide static calendar ──────────────────────────────
        if MARKET_WIDE_2026:
            market_wide = _future_only(MARKET_WIDE_2026)
        else:
            market_wide = []
            warnings.append("static calendar unavailable")

        # ── Persist to catalysts table ───────────────────────────────
        for ev in company_specific:
            try:
                upsert_catalyst(
                    ticker=ticker, event_type=ev["type"], event_date=ev["date"],
                    description=ev["description"], source="yfinance",
                )
            except Exception as e:
                warnings.append(f"upsert_catalyst failed for {ev['type']}: {e}")
        for ev in market_wide:
            try:
                upsert_catalyst(
                    ticker=MARKET_WIDE_TICKER, event_type=ev["type"], event_date=ev["date"],
                    description=ev["description"], source="static_calendar",
                )
            except Exception as e:
                warnings.append(f"upsert_catalyst failed for {ev['type']}: {e}")

        data: Dict[str, Any] = {
            "ticker": ticker,
            "earnings_date": earnings_date,
            "dividend_date": dividend_date,
            "company_specific": company_specific,
            "market_wide": market_wide,
            "warnings": warnings,
            "_confidence": "medium",
        }

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence="medium",
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    if data.get("earnings_date") or data.get("dividend_date"):
        sources.append(Source(
            tool="catalyst_lookup", field="company_specific",
            fetched_at=now,
            url=f"https://finance.yahoo.com/quote/{ticker}/calendar",
            note=f"yfinance Ticker.calendar{suffix}",
        ))
    if data.get("market_wide"):
        sources.append(Source(
            tool="catalyst_lookup", field="market_wide",
            fetched_at=now, url=None,
            note=f"static_calendar (FOMC/CPI/NFP 2026){suffix}",
        ))
    return sources


register(CatalystLookupTool())

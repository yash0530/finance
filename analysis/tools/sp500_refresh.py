"""
tools.sp500_refresh — pull-triggered S&P 500 snapshot rebuild.

Rebuilds analysis/.cache/sp500_data.json from the current cached constituent
list and yfinance fundamentals. This is intentionally pull-based: callers must
invoke the tool or POST route; there is no worker, cron, or background refresh.
"""

from __future__ import annotations

import json
import math
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from tools import Source, Tool, ToolResult, register
from tools.movers import fetch_quotes


_CACHE_PATH = Path(__file__).parent.parent / ".cache" / "sp500_data.json"
_CONSTITUENTS_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_USER_AGENT = "PortfolioIntelligence/1.0"


def _clean_number(value: Any) -> Optional[float]:
    if value in (None, "", "N/A"):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _safe_info(info: Dict[str, Any], key: str) -> Optional[float]:
    return _clean_number(info.get(key))


def _fmt_currency(value: Optional[float]) -> str:
    return "N/A" if value is None else f"${value:,.2f}"


def _fmt_large(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"${value / 1e12:.2f}T"
    if abs(value) >= 1e9:
        return f"${value / 1e9:.2f}B"
    if abs(value) >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"


def _fmt_percent(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def _fmt_multiple(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.2f}x"


def _read_payload(cache_path: Optional[Path] = None) -> Dict[str, Any]:
    cache_path = cache_path or _CACHE_PATH
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _normalize_ticker(ticker: Any) -> str:
    """Normalize S&P symbols to yfinance-compatible tickers."""
    return str(ticker or "").upper().strip().replace(".", "-")


def _cache_constituent_rows(cache_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Constituent metadata from the existing snapshot, used only as fallback."""
    rows = _read_payload(cache_path).get("data") or []
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = _normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        out[ticker] = {
            "ticker": ticker,
            "company_name": row.get("company_name") or ticker,
            "sector": row.get("sector") or "Unknown",
            "industry": row.get("industry") or "",
        }
    return [out[t] for t in sorted(out)]


def _fetch_constituent_rows() -> List[Dict[str, Any]]:
    """Fetch the current S&P 500 constituent table.

    The index has 500 companies but more than 500 listed securities because a
    few companies have multiple share classes. Keep all listed symbols.
    """
    import pandas as pd
    import requests

    response = requests.get(_CONSTITUENTS_URL, headers={"User-Agent": _USER_AGENT}, timeout=20)
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text), attrs={"id": "constituents"})
    if not tables:
        raise ValueError("S&P 500 constituents table not found")

    rows: Dict[str, Dict[str, Any]] = {}
    for _, item in tables[0].iterrows():
        ticker = _normalize_ticker(item.get("Symbol"))
        if not ticker:
            continue
        rows[ticker] = {
            "ticker": ticker,
            "company_name": str(item.get("Security") or ticker).strip(),
            "sector": str(item.get("GICS Sector") or "Unknown").strip() or "Unknown",
            "industry": str(item.get("GICS Sub-Industry") or "").strip(),
        }

    if len(rows) < 450:
        raise ValueError(f"S&P 500 constituent source returned only {len(rows)} rows")
    return [rows[t] for t in sorted(rows)]


def constituent_rows(cache_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Current S&P 500 constituent metadata, falling back to the cache offline."""
    try:
        return _fetch_constituent_rows()
    except Exception:
        return _cache_constituent_rows(cache_path)


def snapshot_status(cache_path: Optional[Path] = None) -> Dict[str, Any]:
    """Return timestamp/count/age metadata for the current snapshot."""
    cache_path = cache_path or _CACHE_PATH
    payload = _read_payload(cache_path)
    timestamp = payload.get("timestamp")
    rows = payload.get("data") or []
    age_seconds = None
    if timestamp:
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                age_seconds = max(0, int((datetime.now() - parsed).total_seconds()))
            else:
                age_seconds = max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))
        except Exception:
            age_seconds = None
    return {
        "exists": cache_path.exists(),
        "timestamp": timestamp,
        "row_count": len(rows),
        "age_seconds": age_seconds,
    }


def seed_tickers(cache_path: Optional[Path] = None) -> List[str]:
    """Use the live S&P 500 constituent source, with the snapshot as fallback."""
    return sorted({r["ticker"] for r in constituent_rows(cache_path) if r.get("ticker")})


def _build_row(
    ticker: str,
    info: Dict[str, Any],
    quote: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = metadata or {}
    current_price = (
        _clean_number((quote or {}).get("price"))
        or _safe_info(info, "currentPrice")
        or _safe_info(info, "regularMarketPrice")
    )
    market_cap = (
        _clean_number((quote or {}).get("market_cap"))
        or _safe_info(info, "marketCap")
    )
    forward_pe = _safe_info(info, "forwardPE")
    trailing_pe = _safe_info(info, "trailingPE")
    pe_ratio = round(trailing_pe / forward_pe, 12) if trailing_pe and forward_pe else None
    high = _safe_info(info, "fiftyTwoWeekHigh")
    low = _safe_info(info, "fiftyTwoWeekLow")
    year_change = _safe_info(info, "52WeekChange")
    day_change = _clean_number((quote or {}).get("change_pct"))
    volume = _clean_number((quote or {}).get("volume"))
    average_volume = _safe_info(info, "averageVolume") or _safe_info(info, "averageDailyVolume10Day")
    volume_ratio = round(volume / average_volume, 4) if volume is not None and average_volume else None
    pct_from_high = ((current_price - high) / high) if current_price is not None and high else None

    return {
        "current_price": current_price,
        "current_price_fmt": _fmt_currency(current_price),
        "market_cap": int(market_cap) if market_cap is not None else None,
        "market_cap_fmt": _fmt_large(market_cap),
        "forward_pe": forward_pe,
        "trailing_pe": trailing_pe,
        "pe_ratio": pe_ratio,
        "pe_ratio_fmt": _fmt_multiple(pe_ratio),
        "peg_ratio": _safe_info(info, "pegRatio"),
        "price_to_sales": _safe_info(info, "priceToSalesTrailing12Months"),
        "price_to_book": _safe_info(info, "priceToBook"),
        "ev_to_revenue": _safe_info(info, "enterpriseToRevenue"),
        "ev_to_ebitda": _safe_info(info, "enterpriseToEbitda"),
        "total_revenue": int(_safe_info(info, "totalRevenue")) if _safe_info(info, "totalRevenue") is not None else None,
        "total_revenue_fmt": _fmt_large(_safe_info(info, "totalRevenue")),
        "net_income": int(_safe_info(info, "netIncomeToCommon")) if _safe_info(info, "netIncomeToCommon") is not None else None,
        "net_income_fmt": _fmt_large(_safe_info(info, "netIncomeToCommon")),
        "profit_margin": _safe_info(info, "profitMargins"),
        "profit_margin_fmt": _fmt_percent(_safe_info(info, "profitMargins")),
        "operating_margin": _safe_info(info, "operatingMargins"),
        "operating_margin_fmt": _fmt_percent(_safe_info(info, "operatingMargins")),
        "gross_margin": _safe_info(info, "grossMargins"),
        "dividend_yield": _safe_info(info, "dividendYield"),
        "dividend_yield_fmt": _fmt_percent(_safe_info(info, "dividendYield")),
        "beta": _safe_info(info, "beta"),
        "eps": _safe_info(info, "trailingEps"),
        "revenue_growth": _safe_info(info, "revenueGrowth"),
        "revenue_growth_fmt": _fmt_percent(_safe_info(info, "revenueGrowth")),
        "year_change": year_change,
        "year_change_fmt": _fmt_percent(year_change),
        "fifty_two_week_high": high,
        "fifty_two_week_low": low,
        "day_change_percent": day_change,
        "day_change_percent_fmt": "N/A" if day_change is None else f"{day_change:.2f}%",
        "volume": int(volume) if volume is not None else None,
        "average_volume": int(average_volume) if average_volume is not None else None,
        "volume_ratio": volume_ratio,
        "volume_ratio_fmt": _fmt_multiple(volume_ratio),
        "fifty_day_average": _safe_info(info, "fiftyDayAverage"),
        "two_hundred_day_average": _safe_info(info, "twoHundredDayAverage"),
        "pct_from_high": pct_from_high,
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or metadata.get("company_name") or ticker,
        "sector": info.get("sector") or metadata.get("sector") or "Unknown",
        "industry": info.get("industry") or metadata.get("industry") or "",
    }


def _write_snapshot(rows: List[Dict[str, Any]], cache_path: Optional[Path] = None) -> Dict[str, Any]:
    cache_path = cache_path or _CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    payload = {"timestamp": timestamp, "data": rows}
    with tempfile.NamedTemporaryFile("w", dir=cache_path.parent, delete=False) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=False)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(cache_path)
    return payload


def rebuild_snapshot(
    tickers: Optional[Iterable[str]] = None,
    max_workers: int = 8,
    cache_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fetch yfinance data and atomically write a fresh S&P 500 snapshot."""
    cache_path = cache_path or _CACHE_PATH
    if tickers is None:
        seed_rows = constituent_rows(cache_path)
    else:
        seed_rows = [{"ticker": _normalize_ticker(t)} for t in tickers]
    metadata_by_ticker = {r["ticker"]: r for r in seed_rows if r.get("ticker")}
    universe = sorted(metadata_by_ticker)
    if not universe:
        raise ValueError("No S&P 500 tickers available to refresh")
    try:
        worker_count = max(1, int(max_workers or 1))
    except (TypeError, ValueError):
        worker_count = 8

    import yfinance as yf

    quotes = fetch_quotes(universe, max_workers=worker_count)

    def _one(ticker: str):
        try:
            info = yf.Ticker(ticker).info or {}
            return ticker, _build_row(ticker, info, quotes.get(ticker), metadata_by_ticker.get(ticker)), None
        except Exception as exc:
            row = _build_row(ticker, {}, quotes.get(ticker), metadata_by_ticker.get(ticker))
            return ticker, row, f"{type(exc).__name__}: {exc}"

    rows: List[Dict[str, Any]] = []
    failures: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        for ticker, row, error in pool.map(_one, universe):
            if row:
                rows.append(row)
            if error:
                failures[ticker] = error

    if not rows:
        raise RuntimeError("No S&P 500 rows resolved from yfinance")

    rows.sort(key=lambda r: r["ticker"])
    payload = _write_snapshot(rows, cache_path)
    return {
        "timestamp": payload["timestamp"],
        "row_count": len(rows),
        "requested_count": len(universe),
        "resolved_count": len(rows) - len(failures),
        "failed_count": len(failures),
        "failures": failures,
        "cache_path": str(cache_path),
        "sample_tickers": [r["ticker"] for r in rows[:5]],
    }


class SP500RefreshTool(Tool):
    name = "sp500_refresh"
    description = (
        "Pull-triggered rebuild of the S&P 500 snapshot cache from yfinance "
        "using a current S&P 500 constituent seed. Writes .cache/sp500_data.json."
    )
    cache_ttl_seconds = 0
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional explicit ticker list; defaults to cached S&P 500 constituents.",
                },
                "max_workers": {
                    "type": "integer",
                    "description": "Parallel yfinance request count, default 8.",
                },
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, tickers: Optional[List[str]] = None, max_workers: int = 8, **kwargs) -> ToolResult:
        data = rebuild_snapshot(tickers=tickers, max_workers=max_workers)
        now = datetime.now().isoformat()
        confidence = "high" if data["resolved_count"] >= max(1, data["requested_count"] * 0.9) else "medium"
        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=[
                Source(
                    tool=self.name,
                    field="sp500_snapshot",
                    fetched_at=now,
                    url=_CONSTITUENTS_URL,
                    note="S&P 500 constituent seed, enriched with yfinance info + fast_info",
                )
            ],
            confidence=confidence,
            cost_usd=0.0,
        )


register(SP500RefreshTool())

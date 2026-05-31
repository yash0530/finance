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
_USER_AGENT = "EdgeTerminal/1.0"
DEFAULT_MAX_WORKERS = 4
DEFAULT_MAX_INFO_REQUESTS = 25
_ENRICHMENT_FIELDS = (
    "forward_pe",
    "trailing_pe",
    "profit_margin",
    "revenue_growth",
    "year_change",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "beta",
    "eps",
)
_MIN_ENRICHMENT_SCORE = 5


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


def _has_value(value: Any) -> bool:
    return _clean_number(value) is not None if isinstance(value, (int, float)) else value not in (None, "", "N/A")


def _enrichment_score(row: Optional[Dict[str, Any]]) -> int:
    if not row:
        return 0
    return sum(1 for field in _ENRICHMENT_FIELDS if _has_value(row.get(field)))


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


def _finalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute derived/display fields after new data is merged with cache."""
    current_price = _clean_number(row.get("current_price"))
    market_cap = _clean_number(row.get("market_cap"))
    forward_pe = _clean_number(row.get("forward_pe"))
    trailing_pe = _clean_number(row.get("trailing_pe"))
    high = _clean_number(row.get("fifty_two_week_high"))
    volume = _clean_number(row.get("volume"))
    average_volume = _clean_number(row.get("average_volume"))

    pe_ratio = _clean_number(row.get("pe_ratio"))
    if pe_ratio is None and trailing_pe is not None and forward_pe not in (None, 0):
        pe_ratio = round(trailing_pe / forward_pe, 12)
    row["pe_ratio"] = pe_ratio

    if current_price is not None and high:
        row["pct_from_high"] = (current_price - high) / high

    if volume is not None:
        row["volume"] = int(volume)
    if average_volume is not None:
        row["average_volume"] = int(average_volume)
    if volume is not None and average_volume:
        row["volume_ratio"] = round(volume / average_volume, 4)

    if market_cap is not None:
        row["market_cap"] = int(market_cap)
    for key in ("total_revenue", "net_income"):
        value = _clean_number(row.get(key))
        if value is not None:
            row[key] = int(value)

    row["current_price_fmt"] = _fmt_currency(current_price)
    row["market_cap_fmt"] = _fmt_large(market_cap)
    row["pe_ratio_fmt"] = _fmt_multiple(row.get("pe_ratio"))
    row["total_revenue_fmt"] = _fmt_large(_clean_number(row.get("total_revenue")))
    row["net_income_fmt"] = _fmt_large(_clean_number(row.get("net_income")))
    row["profit_margin_fmt"] = _fmt_percent(_clean_number(row.get("profit_margin")))
    row["operating_margin_fmt"] = _fmt_percent(_clean_number(row.get("operating_margin")))
    row["dividend_yield_fmt"] = _fmt_percent(_clean_number(row.get("dividend_yield")))
    row["revenue_growth_fmt"] = _fmt_percent(_clean_number(row.get("revenue_growth")))
    row["year_change_fmt"] = _fmt_percent(_clean_number(row.get("year_change")))
    day_change = _clean_number(row.get("day_change_percent"))
    row["day_change_percent_fmt"] = "N/A" if day_change is None else f"{day_change:.2f}%"
    row["volume_ratio_fmt"] = _fmt_multiple(_clean_number(row.get("volume_ratio")))
    return row


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

    return _finalize_row({
        "current_price": current_price,
        "market_cap": market_cap,
        "forward_pe": forward_pe,
        "trailing_pe": trailing_pe,
        "pe_ratio": pe_ratio,
        "peg_ratio": _safe_info(info, "pegRatio"),
        "price_to_sales": _safe_info(info, "priceToSalesTrailing12Months"),
        "price_to_book": _safe_info(info, "priceToBook"),
        "ev_to_revenue": _safe_info(info, "enterpriseToRevenue"),
        "ev_to_ebitda": _safe_info(info, "enterpriseToEbitda"),
        "total_revenue": _safe_info(info, "totalRevenue"),
        "net_income": _safe_info(info, "netIncomeToCommon"),
        "profit_margin": _safe_info(info, "profitMargins"),
        "operating_margin": _safe_info(info, "operatingMargins"),
        "gross_margin": _safe_info(info, "grossMargins"),
        "dividend_yield": _safe_info(info, "dividendYield"),
        "beta": _safe_info(info, "beta"),
        "eps": _safe_info(info, "trailingEps"),
        "revenue_growth": _safe_info(info, "revenueGrowth"),
        "year_change": year_change,
        "fifty_two_week_high": high,
        "fifty_two_week_low": low,
        "day_change_percent": day_change,
        "volume": volume,
        "average_volume": average_volume,
        "volume_ratio": volume_ratio,
        "fifty_day_average": _safe_info(info, "fiftyDayAverage"),
        "two_hundred_day_average": _safe_info(info, "twoHundredDayAverage"),
        "pct_from_high": pct_from_high,
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or metadata.get("company_name") or ticker,
        "sector": metadata.get("sector") or info.get("sector") or "Unknown",
        "industry": metadata.get("industry") or info.get("industry") or "",
    })


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


def _prior_snapshot_rows(cache_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    return {
        _normalize_ticker(row.get("ticker")): dict(row)
        for row in (_read_payload(cache_path).get("data") or [])
        if row.get("ticker")
    }


def _merge_with_previous(
    new_row: Dict[str, Any],
    previous_row: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Overlay non-empty fresh fields onto the prior row.

    Yahoo's full `.info` endpoint can return an empty/sparse payload when it is
    rate-limited. Preserve prior fundamentals in that case while still taking
    fresh fast-quote fields from `new_row`.
    """
    if not previous_row:
        row = dict(new_row)
    else:
        row = dict(previous_row)
        for key, value in new_row.items():
            if key.endswith("_fmt"):
                continue
            if key in {"ticker", "company_name", "sector", "industry"} or _has_value(value):
                row[key] = value

    row["ticker"] = new_row.get("ticker") or row.get("ticker")
    if metadata:
        row["company_name"] = metadata.get("company_name") or row.get("company_name") or row["ticker"]
        row["sector"] = metadata.get("sector") or row.get("sector") or "Unknown"
        row["industry"] = metadata.get("industry") or row.get("industry") or ""
    else:
        row["company_name"] = row.get("company_name") or row["ticker"]
        row["sector"] = row.get("sector") or "Unknown"
        row["industry"] = row.get("industry") or ""
    return _finalize_row(row)


def _fallback_row(
    ticker: str,
    previous_rows: Dict[str, Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
    quote: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    quote_row = _build_row(ticker, {}, quote, metadata)
    return _merge_with_previous(quote_row, previous_rows.get(ticker), metadata)


def rebuild_snapshot(
    tickers: Optional[Iterable[str]] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_info_requests: int = DEFAULT_MAX_INFO_REQUESTS,
    cache_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fetch yfinance data and atomically write a fresh S&P 500 snapshot."""
    cache_path = cache_path or _CACHE_PATH
    if tickers is None:
        seed_rows = constituent_rows(cache_path)
    else:
        seed_rows = [{"ticker": _normalize_ticker(t)} for t in tickers]
    metadata_by_ticker = {r["ticker"]: r for r in seed_rows if r.get("ticker")}
    previous_rows = _prior_snapshot_rows(cache_path)
    universe = sorted(
        metadata_by_ticker,
        key=lambda ticker: (_enrichment_score(previous_rows.get(ticker)), ticker),
    )
    if not universe:
        raise ValueError("No S&P 500 tickers available to refresh")
    try:
        worker_count = max(1, int(max_workers or 1))
    except (TypeError, ValueError):
        worker_count = DEFAULT_MAX_WORKERS

    import yfinance as yf

    quotes = fetch_quotes(universe, max_workers=worker_count)
    incomplete = {
        ticker
        for ticker in universe
        if _enrichment_score(previous_rows.get(ticker)) < _MIN_ENRICHMENT_SCORE
    }
    info_candidates = [ticker for ticker in universe if ticker in incomplete] if incomplete else list(universe)
    try:
        info_request_limit = max(1, int(max_info_requests or DEFAULT_MAX_INFO_REQUESTS))
    except (TypeError, ValueError):
        info_request_limit = DEFAULT_MAX_INFO_REQUESTS
    if tickers is None and len(info_candidates) > info_request_limit:
        info_candidates = info_candidates[:info_request_limit]
    info_tickers = set(info_candidates)
    info_deferred_count = max(0, len(incomplete or universe) - len(info_tickers))

    def _one(ticker: str):
        metadata = metadata_by_ticker.get(ticker)
        quote_row = _build_row(ticker, {}, quotes.get(ticker), metadata)
        if ticker not in info_tickers:
            return ticker, _merge_with_previous(quote_row, previous_rows.get(ticker), metadata), None
        try:
            info = yf.Ticker(ticker).info or {}
            new_row = _build_row(ticker, info, quotes.get(ticker), metadata)
            row = _merge_with_previous(new_row, previous_rows.get(ticker), metadata)
            if _enrichment_score(new_row) == 0:
                return ticker, row, "Sparse yfinance info payload; preserved cached fundamentals where available"
            return ticker, row, None
        except Exception as exc:
            row = _fallback_row(ticker, previous_rows, metadata, quotes.get(ticker))
            return ticker, row, f"{type(exc).__name__}: {exc}"

    rows: List[Dict[str, Any]] = []
    failures: Dict[str, str] = {}
    preserved_count = 0
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        for ticker, row, error in pool.map(_one, universe):
            if row:
                rows.append(row)
                quote_only = _build_row(ticker, {}, quotes.get(ticker), metadata_by_ticker.get(ticker))
                if _enrichment_score(previous_rows.get(ticker)) > _enrichment_score(quote_only):
                    preserved_count += 1
            if error:
                failures[ticker] = error

    if not rows:
        raise RuntimeError("No S&P 500 rows resolved from yfinance")

    rows.sort(key=lambda r: r["ticker"])
    enriched_count = sum(1 for row in rows if _enrichment_score(row) >= _MIN_ENRICHMENT_SCORE)
    payload = _write_snapshot(rows, cache_path)
    return {
        "timestamp": payload["timestamp"],
        "row_count": len(rows),
        "requested_count": len(universe),
        "resolved_count": len(rows) - len(failures),
        "failed_count": len(failures),
        "failures": failures,
        "enriched_count": enriched_count,
        "partial_count": len(rows) - enriched_count,
        "info_requested_count": len(info_tickers),
        "info_deferred_count": info_deferred_count,
        "preserved_count": preserved_count,
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
                    "description": "Optional explicit ticker list; defaults to the current S&P 500 constituent seed.",
                },
                "max_workers": {
                    "type": "integer",
                    "description": f"Parallel yfinance request count, default {DEFAULT_MAX_WORKERS}.",
                },
                "max_info_requests": {
                    "type": "integer",
                    "description": f"Maximum full yfinance info lookups per broad refresh, default {DEFAULT_MAX_INFO_REQUESTS}.",
                },
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(
        self,
        tickers: Optional[List[str]] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        max_info_requests: int = DEFAULT_MAX_INFO_REQUESTS,
        **kwargs,
    ) -> ToolResult:
        data = rebuild_snapshot(tickers=tickers, max_workers=max_workers, max_info_requests=max_info_requests)
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

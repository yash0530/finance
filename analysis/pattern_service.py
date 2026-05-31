"""
pattern_service — chart-pattern scan API helpers.

The detector geometry lives in pattern_detectors.py. This service wires those
detectors to the price_history Tool and the S&P 500 snapshot so pattern scans
stay pull-based, cacheable, and outside the Flask route body.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

PATTERN_CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_SCAN_LIMIT = 150


def _pattern_catalog_map() -> Dict[str, Dict[str, Any]]:
    import pattern_detectors as pd

    return {
        key: {"key": key, "name": meta[0], "signal": meta[1], "detector": meta[2]}
        for key, meta in pd.PATTERN_DETECTORS.items()
    }


def pattern_catalog() -> List[Dict[str, str]]:
    return [
        {"key": key, "name": meta["name"], "signal": meta["signal"]}
        for key, meta in _pattern_catalog_map().items()
    ]


def _normalize_pattern_type(pattern_type: str) -> str:
    return (pattern_type or "").strip().lower().replace("-", "_")


def _format_currency(value: Any) -> Optional[str]:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if abs(n) >= 1e12:
        return f"${n / 1e12:.2f}T"
    if abs(n) >= 1e9:
        return f"${n / 1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n / 1e6:.2f}M"
    return f"${n:,.2f}"


def _bars_for_ticker(ticker: str) -> List[Dict[str, Any]]:
    from tools import get_tool

    result = get_tool("price_history").execute(ticker=ticker.upper(), range="1y")
    if not result.is_ok():
        return []
    return (result.data or {}).get("bars", []) or []


def _company_lookup() -> Dict[str, Dict[str, Any]]:
    try:
        from tools.sp500_lookup import sp500_snapshot
        return sp500_snapshot()
    except Exception:
        return {}


def _detect_one(pattern_key: str, bars: List[Dict[str, Any]], ticker: str,
                company: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    catalog = _pattern_catalog_map()
    meta = catalog.get(pattern_key)
    if not meta or len(bars) < 30:
        return None

    pairs = [(b.get("close"), (b.get("time") or "").split("T")[0]) for b in bars]
    pairs = [(price, date) for price, date in pairs if price is not None and date]
    if len(pairs) < 30:
        return None

    prices = [price for price, _ in pairs]
    dates = [date for _, date in pairs]
    detected = meta["detector"](prices, dates)
    if not isinstance(detected, dict) or not detected.get("detected"):
        return None

    current_price = prices[-1] if prices else None
    enriched = dict(detected)
    enriched.update({
        "ticker": ticker.upper(),
        "type": pattern_key,
        "pattern_type": pattern_key,
        "name": meta["name"],
        "pattern_name": meta["name"],
        "signal": meta["signal"],
        "current_price": current_price,
        "current_price_fmt": _format_currency(current_price),
    })
    if company:
        enriched.update({
            "company_name": company.get("company_name") or company.get("name") or "",
            "sector": company.get("sector") or "",
        })
    if enriched.get("target_price") is not None:
        try:
            enriched["target_price"] = round(float(enriched["target_price"]), 2)
        except (TypeError, ValueError):
            pass
    return enriched


def scan_ticker(ticker: str, pattern_type: Optional[str] = None,
                refresh: bool = False) -> Dict[str, Any]:
    import db

    ticker = ticker.upper().strip()
    pattern_key = _normalize_pattern_type(pattern_type) if pattern_type else "all"
    catalog = _pattern_catalog_map()
    if pattern_type and pattern_key not in catalog:
        raise KeyError(pattern_key)

    cache_key = f"{ticker}:{pattern_key}:v1"
    if not refresh:
        cached = db.get_tool_cache("pattern_scan", cache_key, PATTERN_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    bars = _bars_for_ticker(ticker)
    company = _company_lookup().get(ticker, {})
    keys = [pattern_key] if pattern_type else list(catalog.keys())
    patterns = []
    for key in keys:
        try:
            item = _detect_one(key, bars, ticker, company)
        except Exception:
            item = None
        if item:
            patterns.append(item)

    patterns.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    result = {
        "ticker": ticker,
        "pattern_type": pattern_key if pattern_type else None,
        "detected": bool(patterns),
        "count": len(patterns),
        "patterns": patterns,
    }
    if pattern_type:
        meta = catalog[pattern_key]
        result.update({"pattern_name": meta["name"], "signal": meta["signal"]})
        if patterns:
            result.update(patterns[0])
        else:
            result["message"] = f"No {meta['name']} pattern detected in recent price history"

    db.save_tool_cache("pattern_scan", cache_key, result)
    return result


def _resolve_universe(universe: str, limit: int) -> List[str]:
    universe = (universe or "sp500").lower()
    if universe == "watchlist":
        import db
        tickers = [w["ticker"] for w in db.get_watchlist()]
    elif universe == "themes":
        import themes_service
        tickers = themes_service.all_theme_tickers()
    else:
        from tools.sp500_lookup import sp500_constituents
        tickers = sp500_constituents()

    out = []
    for ticker in tickers:
        t = (ticker or "").upper().strip()
        if t and t not in out:
            out.append(t)
    return out[:max(1, limit)]


def scan_universe(universe: str = "sp500", pattern_type: Optional[str] = None,
                  limit: int = DEFAULT_SCAN_LIMIT, refresh: bool = False) -> Dict[str, Any]:
    import db

    pattern_key = _normalize_pattern_type(pattern_type) if pattern_type else "all"
    catalog = _pattern_catalog_map()
    if pattern_type and pattern_key not in catalog:
        raise KeyError(pattern_key)

    limit = max(1, min(int(limit or DEFAULT_SCAN_LIMIT), 500))
    universe_name = (universe or "sp500").lower()
    cache_key = f"{universe_name}:{pattern_key}:{limit}:v1"
    if not refresh:
        cached = db.get_tool_cache("pattern_scan_universe", cache_key, PATTERN_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    tickers = _resolve_universe(universe_name, limit)
    by_type = {
        key: {"name": meta["name"], "signal": meta["signal"], "count": 0, "patterns": []}
        for key, meta in catalog.items()
    }

    for ticker in tickers:
        for pattern in scan_ticker(ticker, pattern_type=pattern_type, refresh=refresh).get("patterns", []):
            key = pattern.get("pattern_type")
            if key in by_type:
                by_type[key]["patterns"].append(pattern)

    for bucket in by_type.values():
        bucket["patterns"].sort(key=lambda p: p.get("confidence", 0), reverse=True)
        bucket["count"] = len(bucket["patterns"])

    total_bullish = sum(len(b["patterns"]) for b in by_type.values() if b["signal"] == "bullish")
    total_bearish = sum(len(b["patterns"]) for b in by_type.values() if b["signal"] == "bearish")
    result = {
        "title": "Technical Patterns",
        "description": "Detected chart patterns across the selected universe",
        "universe": universe_name,
        "evaluated": len(tickers),
        "limit": limit,
        "pattern_types": by_type,
        "summary": {
            "total_patterns": total_bullish + total_bearish,
            "bullish_patterns": total_bullish,
            "bearish_patterns": total_bearish,
        },
    }
    db.save_tool_cache("pattern_scan_universe", cache_key, result)
    return result

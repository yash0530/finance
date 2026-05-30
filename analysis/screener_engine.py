"""
screener_engine.py — rule-based screener over cached tool data.

Evaluates a rules-JSON spec against a ticker universe. For each ticker it pulls
the (cached) fundamentals + technicals + financial_trends tools, flattens their
fields into a single namespace, and walks the rules. No LLM, no new network
beyond the tools' own (cached) fetches.

Request shape:
{
  "universe": "themes" | "sp500" | "watchlist" | ["NVDA", "AMD"],
  "rules": [
    {"field": "rsi", "op": "<", "value": 30},
    {"field": "ma_50_above_ma_200", "op": "=", "value": true},
    {"field": "yoy_revenue_growth", "op": ">", "value": 0.20}
  ],
  "combine": "AND"
}
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_SP500_LIVE_SCAN_LIMIT = 150
PATTERN_CACHE_TTL_SECONDS = 24 * 60 * 60


# Fields the screener understands, each resolved from the tool result dicts.
# Keeping this explicit (rather than dumping every tool field) keeps the
# screener honest about what it can filter on.
def _field_resolvers() -> Dict[str, Callable[[Dict, Dict, Dict], Optional[Any]]]:
    return {
        # technicals
        "rsi": lambda f, t, tr: t.get("rsi"),
        "ma_50": lambda f, t, tr: t.get("ma_50"),
        "ma_200": lambda f, t, tr: t.get("ma_200"),
        "ma_50_above_ma_200": lambda f, t, tr: t.get("golden_cross"),
        "above_50ma": lambda f, t, tr: t.get("above_50ma"),
        "above_200ma": lambda f, t, tr: t.get("above_200ma"),
        "year_return_pct": lambda f, t, tr: t.get("year_return_pct"),
        "volatility_pct": lambda f, t, tr: t.get("annualized_volatility_pct"),
        "relative_strength_vs_spy": lambda f, t, tr: t.get("relative_strength_vs_spy"),
        # fundamentals
        "price": lambda f, t, tr: f.get("current_price"),
        "market_cap": lambda f, t, tr: f.get("market_cap"),
        "forward_pe": lambda f, t, tr: f.get("forward_pe"),
        "trailing_pe": lambda f, t, tr: f.get("trailing_pe"),
        "profit_margin": lambda f, t, tr: f.get("profit_margin"),
        "revenue_growth": lambda f, t, tr: f.get("revenue_growth"),
        # snapshot-derived (populated for the sp500 universe; None elsewhere)
        "day_change_pct": lambda f, t, tr: f.get("day_change_pct"),
        "year_change_pct": lambda f, t, tr: f.get("year_change_pct"),
        "pct_from_52w_high": lambda f, t, tr: f.get("pct_from_52w_high"),
        "volume": lambda f, t, tr: f.get("volume"),
        "average_volume": lambda f, t, tr: f.get("average_volume"),
        "volume_ratio": lambda f, t, tr: f.get("volume_ratio"),
        # financial_trends
        "yoy_revenue_growth": lambda f, t, tr: _resolve_yoy_revenue_growth(f, t, tr),
        "quarter_count": lambda f, t, tr: tr.get("quarter_count"),
    }


# Fields backed by live per-ticker fetches (technicals) or pattern detection —
# heavy to evaluate across a large universe like the S&P 500.
_TECHNICAL_FIELDS = {
    "rsi", "ma_50", "ma_200", "ma_50_above_ma_200",
    "above_50ma", "above_200ma", "year_return_pct",
    "volatility_pct", "relative_strength_vs_spy",
}


def _as_pct(frac: Any) -> Optional[float]:
    """Fraction (0.43) → percent (43.0). The snapshot stores pct_from_high and
    year_change as fractions, while day_change_percent is already a percent."""
    return round(frac * 100, 2) if isinstance(frac, (int, float)) else None


def _snapshot_to_fundamentals(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map an S&P 500 snapshot row into the screener's fundamentals namespace.

    The `_pct` fields are normalized to percent units so rules read naturally
    (e.g. pct_from_52w_high >= -2 means within 2% of the 52-week high).
    """
    return {
        "current_price": row.get("current_price"),
        "market_cap": row.get("market_cap"),
        "forward_pe": row.get("forward_pe"),
        "trailing_pe": row.get("trailing_pe") or row.get("pe_ratio"),
        "profit_margin": row.get("profit_margin"),
        "revenue_growth": row.get("revenue_growth"),
        "day_change_pct": row.get("day_change_percent"),
        "year_change_pct": _as_pct(row.get("year_change")),
        "pct_from_52w_high": _as_pct(row.get("pct_from_high")),
        "volume": row.get("volume"),
        "average_volume": row.get("average_volume"),
        "volume_ratio": row.get("volume_ratio"),
    }


def _detect_patterns(ticker: str) -> set:
    """Names of chart patterns currently detected for a ticker, from cached OHLC."""
    from tools import get_tool
    import pattern_detectors as pd
    try:
        import db
        cached = db.get_tool_cache("screener_patterns", ticker.upper(), PATTERN_CACHE_TTL_SECONDS)
        if cached is not None:
            return set(cached.get("patterns") or [])
    except Exception:
        pass

    try:
        r = get_tool("price_history").execute(ticker=ticker, range="1y")
        bars = (r.data or {}).get("bars", []) if r.is_ok() else []
    except Exception:
        return set()
    if len(bars) < 30:
        return set()
    prices = [b["close"] for b in bars]
    dates = [b["time"] for b in bars]
    found = set()
    for name, detector in pd.PATTERN_DETECTORS.items():
        try:
            res = detector(prices, dates)
            if isinstance(res, dict) and res.get("detected"):
                found.add(name)
        except Exception:
            continue
    try:
        import db
        db.save_tool_cache("screener_patterns", ticker.upper(), {"patterns": sorted(found)})
    except Exception:
        pass
    return found


def _resolve_yoy_revenue_growth(f: Dict, t: Dict, tr: Dict) -> Optional[float]:
    signals = tr.get("trend_signals") or tr.get("signals") or {}
    rates = signals.get("revenue_growth_rates")
    if isinstance(rates, list) and len(rates) > 0:
        try:
            return float(rates[-1]) / 100.0
        except (ValueError, TypeError):
            pass
    return f.get("revenue_growth")


def _trend_value(trends: Dict, key: str, fallback: Any = None) -> Any:
    signals = trends.get("trend_signals") or trends.get("signals") or {}
    if key in signals:
        return signals[key]
    if key in trends:
        return trends[key]
    return fallback


_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: a == b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def available_fields() -> List[str]:
    return sorted(list(_field_resolvers().keys()) + ["pattern"])


def pattern_names() -> List[str]:
    import pattern_detectors as pd
    return list(pd.PATTERN_DETECTORS.keys())


def resolve_universe(spec: Union[str, List[str]]) -> List[str]:
    """Resolve a universe spec to a ticker list."""
    if isinstance(spec, list):
        return [t.upper().strip() for t in spec if t]
    if spec == "watchlist":
        import db
        return [w["ticker"] for w in db.get_watchlist()]
    if spec == "themes":
        import themes_service
        return themes_service.all_theme_tickers()
    if spec == "sp500":
        from tools.sp500_lookup import sp500_constituents
        constituents = sp500_constituents()
        if constituents:
            return constituents
        # Snapshot cache unavailable — fall back to the theme universe.
        import themes_service
        return themes_service.all_theme_tickers()
    return []


def _gather_ticker_data(ticker: str, snapshot_row: Optional[Dict] = None,
                        fetch_technical: bool = True) -> Dict[str, Dict]:
    """Assemble a ticker's data namespaces.

    When `snapshot_row` is given (S&P 500 universe), fundamentals come from the
    snapshot with no live fetch. Technicals/trends are fetched only when
    `fetch_technical` is set, keeping broad scans cheap unless a rule needs them.
    """
    from tools import get_tool
    out = {"fundamentals": {}, "technicals": {}, "trends": {}}

    if snapshot_row is not None:
        out["fundamentals"] = _snapshot_to_fundamentals(snapshot_row)
    else:
        try:
            r = get_tool("fundamentals").execute(ticker=ticker)
            out["fundamentals"] = r.data if r.is_ok() else {}
        except Exception:
            pass

    if fetch_technical:
        try:
            r = get_tool("technicals").execute(ticker=ticker)
            out["technicals"] = r.data if r.is_ok() else {}
        except Exception:
            pass
        try:
            r = get_tool("financial_trends").execute(ticker=ticker)
            out["trends"] = r.data if r.is_ok() else {}
        except Exception:
            pass
    return out


def _evaluate_rule(rule: Dict, f: Dict, t: Dict, tr: Dict,
                   detected_patterns: Optional[set] = None) -> Optional[bool]:
    """Return True/False for a rule, or None if the field is unavailable."""
    field = rule.get("field")
    op = rule.get("op")
    target = rule.get("value")

    if field == "pattern":
        if detected_patterns is None:
            return None
        present = target in detected_patterns
        if op in ("is", "=", "=="):
            return present
        if op in ("is_not", "!="):
            return not present
        return None

    resolver = _field_resolvers().get(field)
    if resolver is None or op not in _OPS:
        return None
    actual = resolver(f, t, tr)
    if actual is None:
        return None
    try:
        return _OPS[op](actual, target)
    except TypeError:
        return None


def run_screen(spec: Dict[str, Any], max_workers: int = 8) -> Dict[str, Any]:
    """Evaluate the rules against the universe; return matched tickers + values."""
    universe_spec = spec.get("universe", "themes")
    universe = resolve_universe(universe_spec)
    rules = spec.get("rules", []) or []
    combine = (spec.get("combine") or "AND").upper()
    scan = bool(spec.get("scan"))
    try:
        max_scan = int(spec.get("max_scan") or DEFAULT_SP500_LIVE_SCAN_LIMIT)
    except (TypeError, ValueError):
        max_scan = DEFAULT_SP500_LIVE_SCAN_LIMIT
    max_scan = max(1, min(max_scan, len(universe) if universe else DEFAULT_SP500_LIVE_SCAN_LIMIT))

    base = {"rules": rules, "combine": combine, "universe": universe_spec}
    if not universe:
        return {**base, "matches": [], "evaluated": 0, "error": "empty universe"}
    if not rules:
        return {**base, "matches": [], "evaluated": 0, "error": "no rules"}

    fields_used = {r.get("field") for r in rules}
    needs_pattern = "pattern" in fields_used
    needs_technical = needs_pattern or bool(fields_used & _TECHNICAL_FIELDS)

    is_sp500 = universe_spec == "sp500"
    if is_sp500:
        from tools.sp500_lookup import sp500_snapshot
        snapshot = sp500_snapshot()
    else:
        snapshot = {}

    # A technical/pattern screen over the full S&P 500 means a live fetch per
    # name — slow + rate-limited. Require an explicit opt-in scan.
    if is_sp500 and needs_technical and not scan:
        return {**base, "matches": [], "evaluated": len(universe),
                "error": "needs_scan",
                "message": ("Technical/pattern rules over the S&P 500 require a live scan "
                            "(slow). Re-run with scan enabled, or narrow the universe."),
                "needs_scan": True}

    requested_universe_count = len(universe)
    scan_limited = False
    if is_sp500 and needs_technical and scan and len(universe) > max_scan:
        universe = universe[:max_scan]
        scan_limited = True

    resolvers = _field_resolvers()

    def _eval_ticker(ticker: str):
        data = _gather_ticker_data(
            ticker, snapshot_row=snapshot.get(ticker) if is_sp500 else None,
            fetch_technical=needs_technical,
        )
        f, t, tr = data["fundamentals"], data["technicals"], data["trends"]
        detected = _detect_patterns(ticker) if needs_pattern else None

        evaluations, missing_fields = [], []
        for r in rules:
            res = _evaluate_rule(r, f, t, tr, detected_patterns=detected)
            if res is None:
                evaluations.append(None)
                missing_fields.append(r.get("field"))
            else:
                evaluations.append(res)

        considered = [e for e in evaluations if e is not None]
        if not considered:
            return None
        passed = any(considered) if combine == "OR" else all(considered)
        if not passed:
            return None

        values = {}
        for r in rules:
            field = r.get("field")
            if field == "pattern":
                values["pattern"] = sorted(detected) if detected else []
            elif resolvers.get(field):
                values[field] = resolvers[field](f, t, tr)

        out = {"ticker": ticker, "values": values}
        if missing_fields:
            out["partial"] = True
            out["missing_fields"] = missing_fields
        return out

    matches: List[Dict] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(universe)))) as pool:
        for result in pool.map(_eval_ticker, universe):
            if result is not None:
                matches.append(result)

    matches.sort(key=lambda m: m["ticker"])
    out = {**base, "matches": matches, "evaluated": len(universe), "matched": len(matches)}
    if scan_limited:
        out.update({
            "scan_limited": True,
            "requested_universe_count": requested_universe_count,
            "max_scan": max_scan,
            "message": f"Live scan capped at {max_scan} of {requested_universe_count} S&P 500 tickers.",
        })
    return out

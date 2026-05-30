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
        # financial_trends
        "yoy_revenue_growth": lambda f, t, tr: _resolve_yoy_revenue_growth(f, t, tr),
        "quarter_count": lambda f, t, tr: tr.get("quarter_count"),
    }


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
    return sorted(_field_resolvers().keys())


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
        # Use the theme universe as the free-tier proxy for a broad scan.
        import themes_service
        return themes_service.all_theme_tickers()
    return []


def _gather_ticker_data(ticker: str) -> Dict[str, Dict]:
    from tools import get_tool
    out = {"fundamentals": {}, "technicals": {}, "trends": {}}
    try:
        r = get_tool("fundamentals").execute(ticker=ticker)
        out["fundamentals"] = r.data if r.is_ok() else {}
    except Exception:
        pass
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


def _evaluate_rule(rule: Dict, f: Dict, t: Dict, tr: Dict) -> Optional[bool]:
    """Return True/False for a rule, or None if the field is unavailable."""
    resolvers = _field_resolvers()
    field = rule.get("field")
    op = rule.get("op")
    target = rule.get("value")
    resolver = resolvers.get(field)
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
    universe = resolve_universe(spec.get("universe", "themes"))
    rules = spec.get("rules", []) or []
    combine = (spec.get("combine") or "AND").upper()

    if not universe:
        return {"matches": [], "evaluated": 0, "rules": rules, "combine": combine,
                "error": "empty universe"}
    if not rules:
        return {"matches": [], "evaluated": 0, "rules": rules, "combine": combine,
                "error": "no rules"}

    resolvers = _field_resolvers()

    def _eval_ticker(ticker: str):
        data = _gather_ticker_data(ticker)
        f, t, tr = data["fundamentals"], data["technicals"], data["trends"]
        
        evaluations = []
        missing_fields = []
        for r in rules:
            field = r.get("field")
            res = _evaluate_rule(r, f, t, tr)
            if res is None:
                evaluations.append(None)
                missing_fields.append(field)
            else:
                evaluations.append(res)

        considered = [e for e in evaluations if e is not None]
        if not considered:
            return None

        if combine == "OR":
            passed = any(considered)
        else:
            # AND requires all evaluable rules to pass
            passed = all(considered)

        if not passed:
            return None

        snapshot = {}
        for r in rules:
            field = r.get("field")
            res = resolvers.get(field)
            if res:
                snapshot[field] = res(f, t, tr)
                
        out = {"ticker": ticker, "values": snapshot}
        if len(missing_fields) > 0:
            out["partial"] = True
            out["missing_fields"] = missing_fields
        return out

    matches: List[Dict] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(universe)))) as pool:
        for result in pool.map(_eval_ticker, universe):
            if result is not None:
                matches.append(result)

    matches.sort(key=lambda m: m["ticker"])
    return {
        "matches": matches,
        "evaluated": len(universe),
        "matched": len(matches),
        "rules": rules,
        "combine": combine,
    }

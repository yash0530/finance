"""
tools.macro_context — global macro regime snapshot.

Pulls a handful of indices via yfinance (no ticker required) and derives
yield-curve slope, VIX regime, dollar trend, credit-bond returns, and an
overall "risk on / risk off / mixed" classification.  Cached for 1h.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


# Primary tickers and any fallbacks (try in order, first non-empty wins)
TICKER_PLAN = {
    "yield_10y":  ["^TNX"],
    "yield_30y":  ["^TYX"],
    "yield_short": ["^IRX", "^FVX"],
    "vix":        ["^VIX"],
    "vix9d":      ["^VIX9D"],
    "dxy":        ["DX-Y.NYB", "UUP"],
    "hyg":        ["HYG"],
    "lqd":        ["LQD"],
    "sp500":      ["^GSPC"],
}


def _fetch_history(ticker: str, period: str = "1y"):
    """Best-effort yfinance history fetch.  Returns DataFrame or None."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist is None or getattr(hist, "empty", True):
            return None
        return hist
    except Exception:
        return None


def _fetch_first_available(candidates: List[str], period: str = "1y") -> Tuple[Optional[str], Optional[Any]]:
    for t in candidates:
        h = _fetch_history(t, period=period)
        if h is not None:
            return t, h
    return None, None


def _last_close(hist) -> Optional[float]:
    try:
        if hist is None or hist.empty or "Close" not in hist.columns:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def _pct_change_n_days(hist, n: int) -> Optional[float]:
    try:
        if hist is None or hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < n + 1:
            return None
        prev = float(closes.iloc[-(n + 1)])
        last = float(closes.iloc[-1])
        if prev == 0:
            return None
        return (last - prev) / prev * 100.0
    except Exception:
        return None


def _pct_from_ma(hist, window: int) -> Optional[float]:
    try:
        if hist is None or hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < window:
            return None
        ma = float(closes.tail(window).mean())
        last = float(closes.iloc[-1])
        if ma == 0:
            return None
        return (last - ma) / ma * 100.0
    except Exception:
        return None


def _vix_regime(v: Optional[float]) -> str:
    if v is None:
        return "unknown"
    if v < 15:
        return "low"
    if v < 20:
        return "normal"
    if v < 30:
        return "elevated"
    return "high"


def _classify_regime(vix, inverted, hyg_30d) -> Tuple[str, str]:
    """Return (regime, one-sentence summary)."""
    risk_on = (
        vix is not None and vix < 20
        and hyg_30d is not None and hyg_30d > 0
        and inverted is False
    )
    risk_off = (
        (vix is not None and vix > 25)
        or (inverted is True and hyg_30d is not None and hyg_30d < 0)
    )
    if risk_on:
        regime = "risk_on"
        summary = "Risk-on conditions: VIX subdued, credit firm, curve non-inverted."
    elif risk_off:
        regime = "risk_off"
        summary = "Risk-off conditions: elevated VIX and/or inverted curve with weak credit."
    else:
        regime = "mixed"
        summary = "Mixed regime: cross-currents between volatility, credit, and the curve."
    return regime, summary


class MacroContextTool(Tool):
    name = "macro_context"
    description = (
        "Global macro snapshot from yfinance indices: 10y/2y-proxy yields and "
        "curve slope, VIX level + term structure, DXY trend, HYG/LQD credit "
        "returns, S&P 500 vs 50/200 DMA, and an overall risk_on / risk_off / "
        "mixed regime classification. Cached 1h."
    )
    cache_ttl_seconds = 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Optional ticker (ignored — this tool is global).",
                },
            },
            "required": [],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, **kwargs) -> ToolResult:
        cache_key = "global"
        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(cached, cached=True),
                confidence=cached.get("_confidence", "medium"),
                cached=True,
            )

        warnings: List[str] = []
        fetched: Dict[str, Any] = {}
        chosen_tickers: Dict[str, Optional[str]] = {}
        for slot, candidates in TICKER_PLAN.items():
            tk, hist = _fetch_first_available(candidates)
            chosen_tickers[slot] = tk
            fetched[slot] = hist
            if hist is None:
                warnings.append(f"{slot}: no data from {candidates}")
            elif tk != candidates[0]:
                warnings.append(f"{slot}: fell back from {candidates[0]} to {tk}")

        # ── Yields ─────────────────────────────────────────────────────
        yield_10y = _last_close(fetched["yield_10y"])
        yield_2y_proxy = _last_close(fetched["yield_short"])
        slope_bps = None
        inverted: Optional[bool] = None
        if yield_10y is not None and yield_2y_proxy is not None:
            slope_bps = (yield_10y - yield_2y_proxy) * 100.0
            inverted = slope_bps < 0

        # ── VIX ────────────────────────────────────────────────────────
        vix = _last_close(fetched["vix"])
        vix9d = _last_close(fetched["vix9d"])
        vix_term = None
        in_backwardation = None
        if vix and vix9d:
            vix_term = vix9d / vix
            in_backwardation = vix_term < 1.0

        # ── DXY ────────────────────────────────────────────────────────
        dxy = _last_close(fetched["dxy"])
        dxy_30d = _pct_change_n_days(fetched["dxy"], 30)

        # ── Credit bonds ───────────────────────────────────────────────
        hyg_30d = _pct_change_n_days(fetched["hyg"], 30)
        lqd_30d = _pct_change_n_days(fetched["lqd"], 30)
        # Use credit spread proxy = HYG_return - LQD_return as a simple gauge
        credit_spread_proxy = None
        if hyg_30d is not None and lqd_30d is not None:
            credit_spread_proxy = round(hyg_30d - lqd_30d, 3)

        # ── S&P 500 ────────────────────────────────────────────────────
        sp_50 = _pct_from_ma(fetched["sp500"], 50)
        sp_200 = _pct_from_ma(fetched["sp500"], 200)

        regime, regime_summary = _classify_regime(vix, inverted, hyg_30d)

        # Degrade confidence if many fields are missing
        critical = [yield_10y, vix, dxy, hyg_30d, sp_50]
        missing = sum(1 for v in critical if v is None)
        if missing >= 3:
            confidence = "low"
        elif missing >= 1:
            confidence = "medium"
        else:
            confidence = "high"

        data: Dict[str, Any] = {
            "yield_10y": yield_10y,
            "yield_2y_proxy": yield_2y_proxy,
            "yield_curve_slope_bps": round(slope_bps, 2) if slope_bps is not None else None,
            "yield_curve_inverted": inverted,
            "vix": vix,
            "vix_regime": _vix_regime(vix),
            "vix_term_structure": round(vix_term, 3) if vix_term is not None else None,
            "vix_in_backwardation": in_backwardation,
            "dxy": dxy,
            "dxy_30d_change_pct": round(dxy_30d, 3) if dxy_30d is not None else None,
            "hyg_30d_return_pct": round(hyg_30d, 3) if hyg_30d is not None else None,
            "lqd_30d_return_pct": round(lqd_30d, 3) if lqd_30d is not None else None,
            "credit_spread_proxy": credit_spread_proxy,
            "sp500_pct_from_50dma": round(sp_50, 3) if sp_50 is not None else None,
            "sp500_pct_from_200dma": round(sp_200, 3) if sp_200 is not None else None,
            "sector_rs": None,  # v1 placeholder
            "regime": regime,
            "regime_summary": regime_summary,
            "snapshot_date": datetime.now().date().isoformat(),
            "tickers_used": chosen_tickers,
            "warnings": warnings,
            "_confidence": confidence,
        }

        save_tool_cache(self.name, cache_key, data)

        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(data, cached=False),
            confidence=confidence,
        )


def _build_sources(data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    chosen = data.get("tickers_used") or {}
    pairs = [
        ("yield_10y",              "yield_10y"),
        ("yield_2y_proxy",         "yield_short"),
        ("yield_curve_slope_bps",  "yield_10y"),
        ("vix",                    "vix"),
        ("vix_term_structure",     "vix9d"),
        ("dxy",                    "dxy"),
        ("hyg_30d_return_pct",     "hyg"),
        ("lqd_30d_return_pct",     "lqd"),
        ("sp500_pct_from_50dma",   "sp500"),
        ("sp500_pct_from_200dma",  "sp500"),
    ]
    sources: List[Source] = []
    for field_name, slot in pairs:
        if data.get(field_name) is None:
            continue
        tk = chosen.get(slot)
        url = f"https://finance.yahoo.com/quote/{tk}" if tk else None
        sources.append(Source(
            tool="macro_context", field=field_name,
            fetched_at=now, url=url,
            note=f"yfinance history for {tk or slot}{suffix}",
        ))
    return sources


register(MacroContextTool())

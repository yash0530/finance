"""
tools.options_flow — Options-chain analytics via yfinance.

Computes for the nearest 2-3 expirations:
  - Put/call OI ratio (volume + OI weighted)
  - ATM IV (avg of nearest-strike call + put IVs)
  - A simplified IV "rank" proxy (current ATM IV vs. mean IV across strikes)
  - Unusual contracts: top 5 by volume/OI ratio (>2 = unusual)
  - Net-premium directional proxy: sum(call_vol*price) - sum(put_vol*price)
  - Skew proxy: OTM put IV / OTM call IV at a similar moneyness offset

Persists a snapshot to options_metrics_cache. Cached 4h via generic cache.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tools import Source, Tool, ToolResult, register
from db import get_connection, get_tool_cache, save_tool_cache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _df_to_records(df) -> List[Dict[str, Any]]:
    if df is None:
        return []
    try:
        import pandas as pd
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


def _underlying_price(ticker_obj) -> Optional[float]:
    """Try a few yfinance shapes to pull the current price."""
    # Fast path: .info or .fast_info
    for attr in ("fast_info", "info"):
        try:
            obj = getattr(ticker_obj, attr, None)
            if obj is None:
                continue
            if hasattr(obj, "__getitem__"):
                for k in ("last_price", "regularMarketPrice", "lastPrice", "currentPrice"):
                    try:
                        v = obj[k] if k in obj else None
                    except Exception:
                        v = None
                    f = _safe_float(v)
                    if f and f > 0:
                        return f
            for k in ("last_price", "regularMarketPrice", "currentPrice"):
                v = getattr(obj, k, None)
                f = _safe_float(v)
                if f and f > 0:
                    return f
        except Exception:
            continue
    # Slow path: history()
    try:
        hist = ticker_obj.history(period="1d")
        if hist is not None and not hist.empty:
            return _safe_float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _analyse_chain(
    calls: List[Dict[str, Any]],
    puts: List[Dict[str, Any]],
    underlying: float,
    expiration: str,
) -> Dict[str, Any]:
    """Return per-expiration aggregates."""
    def sum_field(rows, field):
        return sum(_safe_float(r.get(field)) or 0 for r in rows)

    call_oi = sum_field(calls, "openInterest")
    put_oi = sum_field(puts, "openInterest")
    call_vol = sum_field(calls, "volume")
    put_vol = sum_field(puts, "volume")

    # Net premium proxy: use lastPrice (or mid of bid/ask if available)
    def row_price(r):
        last = _safe_float(r.get("lastPrice"))
        if last and last > 0:
            return last
        bid = _safe_float(r.get("bid")) or 0
        ask = _safe_float(r.get("ask")) or 0
        if bid > 0 and ask > 0:
            return (bid + ask) / 2.0
        return last or 0.0

    call_premium = sum((_safe_float(r.get("volume")) or 0) * row_price(r) for r in calls)
    put_premium = sum((_safe_float(r.get("volume")) or 0) * row_price(r) for r in puts)
    net_premium = (call_premium - put_premium) * 100  # contract multiplier

    # ATM strike: closest to underlying
    def closest(rows):
        if not rows:
            return None
        return min(rows, key=lambda r: abs((_safe_float(r.get("strike")) or 0) - underlying))

    atm_call = closest(calls)
    atm_put = closest(puts)
    atm_ivs = [
        _safe_float(atm_call.get("impliedVolatility")) if atm_call else None,
        _safe_float(atm_put.get("impliedVolatility")) if atm_put else None,
    ]
    atm_ivs = [v for v in atm_ivs if v is not None and v > 0]
    atm_iv = sum(atm_ivs) / len(atm_ivs) if atm_ivs else None

    # Mean IV across strikes for an IV rank proxy
    all_ivs = [
        v for v in (
            [_safe_float(r.get("impliedVolatility")) for r in calls]
            + [_safe_float(r.get("impliedVolatility")) for r in puts]
        ) if v is not None and v > 0
    ]
    mean_iv = sum(all_ivs) / len(all_ivs) if all_ivs else None

    # Skew proxy: OTM put IV (strike ~10% below) vs OTM call IV (~10% above)
    def iv_at_offset(rows, target_strike):
        if not rows:
            return None
        nearest = min(rows, key=lambda r: abs((_safe_float(r.get("strike")) or 0) - target_strike))
        return _safe_float(nearest.get("impliedVolatility"))

    skew = None
    if underlying:
        otm_put_iv = iv_at_offset(puts, underlying * 0.9)
        otm_call_iv = iv_at_offset(calls, underlying * 1.1)
        if otm_put_iv and otm_call_iv and otm_call_iv > 0:
            skew = round(otm_put_iv / otm_call_iv, 4)

    # Unusual contracts: vol/OI > 2 (only for rows with OI >= 50 to avoid noise)
    unusual: List[Dict[str, Any]] = []
    for kind, rows in (("call", calls), ("put", puts)):
        for r in rows:
            oi = _safe_float(r.get("openInterest")) or 0
            vol = _safe_float(r.get("volume")) or 0
            if oi >= 50 and vol > 0:
                ratio = vol / oi
                if ratio > 2:
                    unusual.append({
                        "contract": str(r.get("contractSymbol") or ""),
                        "type": kind,
                        "strike": _safe_float(r.get("strike")) or 0.0,
                        "exp": expiration,
                        "volume": int(vol),
                        "oi": int(oi),
                        "ratio": round(ratio, 3),
                    })

    return {
        "expiration": expiration,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "call_vol": call_vol,
        "put_vol": put_vol,
        "atm_iv": atm_iv,
        "mean_iv": mean_iv,
        "net_premium": net_premium,
        "skew_proxy": skew,
        "unusual": unusual,
    }


def _persist_snapshot(
    ticker: str,
    iv_rank: Optional[float],
    pc_ratio: Optional[float],
    skew: Optional[float],
    unusual: List[Dict[str, Any]],
) -> None:
    conn = get_connection()
    try:
        snapshot_date = datetime.now().date().isoformat()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO options_metrics_cache
               (ticker, snapshot_date, iv_rank, iv_percentile, put_call_ratio,
                skew, unusual_json, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticker, snapshot_date) DO UPDATE SET
                 iv_rank = excluded.iv_rank,
                 iv_percentile = excluded.iv_percentile,
                 put_call_ratio = excluded.put_call_ratio,
                 skew = excluded.skew,
                 unusual_json = excluded.unusual_json,
                 fetched_at = excluded.fetched_at""",
            (
                ticker, snapshot_date,
                iv_rank, iv_rank,  # IV percentile == IV rank in our proxy
                pc_ratio, skew,
                json.dumps(unusual, default=str),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class OptionsFlowTool(Tool):
    name = "options_flow"
    description = (
        "Options-chain analytics for a US-listed ticker via yfinance: "
        "put/call ratio (OI + volume), ATM IV, IV rank proxy, skew proxy, "
        "unusual contracts (vol/OI >2), and net-premium directional flow. "
        "Cached 4h."
    )
    cache_ttl_seconds = 4 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "max_expirations": {"type": "integer", "default": 3},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, max_expirations: int = 3, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        now_iso = datetime.now().isoformat()

        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached=True),
                confidence="high",
                cached=True,
            )

        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            expirations = list(getattr(t, "options", []) or [])
        except Exception as e:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"yfinance options unavailable: {type(e).__name__}: {e}",
                confidence="low",
            )

        if not expirations:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"No options listed for {ticker}",
                confidence="low",
            )

        underlying = _underlying_price(t)
        if not underlying:
            return ToolResult(
                tool_name=self.name, data={},
                error="Could not determine underlying price",
                confidence="low",
            )

        used = expirations[: max(1, min(max_expirations, len(expirations)))]
        per_exp: List[Dict[str, Any]] = []
        for exp in used:
            try:
                chain = t.option_chain(exp)
                calls = _df_to_records(getattr(chain, "calls", None))
                puts = _df_to_records(getattr(chain, "puts", None))
            except Exception as e:
                logger.warning(f"option_chain({exp}) failed: {e}")
                continue
            per_exp.append(_analyse_chain(calls, puts, underlying, exp))

        if not per_exp:
            return ToolResult(
                tool_name=self.name, data={},
                error="No option chain data could be parsed",
                confidence="low",
            )

        total_call_oi = sum(p["call_oi"] for p in per_exp)
        total_put_oi = sum(p["put_oi"] for p in per_exp)
        total_call_vol = sum(p["call_vol"] for p in per_exp)
        total_put_vol = sum(p["put_vol"] for p in per_exp)

        pc_oi = round(total_put_oi / total_call_oi, 4) if total_call_oi else None
        pc_vol = round(total_put_vol / total_call_vol, 4) if total_call_vol else None

        atm_ivs = [p["atm_iv"] for p in per_exp if p["atm_iv"]]
        mean_ivs = [p["mean_iv"] for p in per_exp if p["mean_iv"]]
        atm_iv = sum(atm_ivs) / len(atm_ivs) if atm_ivs else None
        mean_iv = sum(mean_ivs) / len(mean_ivs) if mean_ivs else None

        # IV rank proxy: where current ATM IV sits between min and max IV
        # observed across listed strikes. Documented limitation: not a true
        # historical IV rank.
        iv_rank_proxy: Optional[float] = None
        all_ivs_flat: List[float] = []
        # We only have per-exp aggregates here; estimate range using mean_iv as a single point.
        if atm_iv is not None and mean_ivs:
            mn, mx = min(mean_ivs), max(mean_ivs)
            if mx > mn:
                iv_rank_proxy = round((atm_iv - mn) / (mx - mn), 4)
            else:
                iv_rank_proxy = 0.5

        unusual_all: List[Dict[str, Any]] = []
        for p in per_exp:
            unusual_all.extend(p["unusual"])
        unusual_all.sort(key=lambda r: r["ratio"], reverse=True)
        unusual_top = unusual_all[:5]

        skews = [p["skew_proxy"] for p in per_exp if p["skew_proxy"]]
        skew_overall = round(sum(skews) / len(skews), 4) if skews else None

        net_premium = sum(p["net_premium"] for p in per_exp)

        data = {
            "ticker": ticker,
            "underlying_price": underlying,
            "expirations_used": used,
            "atm_iv": atm_iv,
            "iv_rank_proxy": iv_rank_proxy,
            "iv_rank_proxy_note": (
                "Proxy only: position of current ATM IV between min/max of "
                "per-expiration mean IVs across used expirations — NOT a true "
                "trailing-N-day historical IV rank."
            ),
            "put_call_ratio_oi": pc_oi,
            "put_call_ratio_volume": pc_vol,
            "unusual_contracts": unusual_top,
            "skew_proxy": skew_overall,
            "net_premium_proxy": round(net_premium, 2),
            "snapshot_date": datetime.now().date().isoformat(),
            "fetched_at": now_iso,
        }

        # Persist snapshot (best-effort)
        try:
            _persist_snapshot(ticker, iv_rank_proxy, pc_oi, skew_overall, unusual_top)
        except Exception as e:
            logger.warning(f"Failed to persist options snapshot: {e}")

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, cached=False),
            confidence="high" if atm_iv else "medium",
        )


def _build_sources(ticker: str, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    url = f"https://finance.yahoo.com/quote/{ticker}/options"
    return [
        Source(
            tool="options_flow", field=field_name,
            fetched_at=now, url=url,
            note=f"yfinance options chain{suffix}",
        )
        for field_name in (
            "put_call_ratio_oi", "put_call_ratio_volume",
            "atm_iv", "iv_rank_proxy", "skew_proxy",
            "unusual_contracts", "net_premium_proxy",
        )
    ]


register(OptionsFlowTool())

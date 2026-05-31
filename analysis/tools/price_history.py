"""
tools.price_history — OHLCV candlestick bars for a ticker.

Backs the GET /api/chart/<T> endpoint. Pulls bars from yfinance for a given
range/interval and returns them as a list of {time, open, high, low, close,
volume} rows suitable for a candlestick chart. Cached by (ticker, range,
interval) with a TTL that scales with bar size.

POLYGON_API_KEY is a documented data-tier upgrade for true intraday minute
ticks; it is gated inside _execute and unused on the free tier.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from tools import Source, Tool, ToolResult, register
from db import get_connection, get_tool_cache, save_tool_cache


RANGE_TO_YF: Dict[str, Tuple[str, str]] = {
    "1d": ("1d", "5m"),
    "5d": ("5d", "30m"),
    "1m": ("1mo", "1d"),
    "3m": ("3mo", "1d"),
    "1y": ("1y", "1d"),
    "5y": ("5y", "1wk"),
}

# Bump when the cached `data` shape changes so stale entries (written by an
# older code version) are bypassed instead of served. v2 added overlays incl.
# rsi + macd.
_CACHE_VERSION = "v2"

_TTL_BY_RANGE: Dict[str, int] = {
    "1d": 5 * 60,
    "5d": 15 * 60,
    "1m": 60 * 60,
    "3m": 60 * 60,
    "1y": 6 * 60 * 60,
    "5y": 24 * 60 * 60,
}


def _bars_from_history(hist) -> List[Dict[str, Any]]:
    bars: List[Dict[str, Any]] = []
    for idx, row in hist.iterrows():
        ts = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
        try:
            bars.append({
                "time": ts,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]) if row.get("Volume") == row.get("Volume") else None,
            })
        except (KeyError, ValueError, TypeError):
            continue
    return bars


def _fetch_yahoo_chart(ticker: str, period: str, interval: str) -> List[Dict[str, Any]]:
    """Fallback to Yahoo's chart endpoint when yfinance is rate-limited."""
    import requests

    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}",
    ]
    params = {
        "range": period,
        "interval": interval,
        "events": "history",
        "includeAdjustedClose": "true",
    }
    last_error = None
    payload = {}
    for url in urls:
        try:
            res = requests.get(
                url,
                params=params,
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            res.raise_for_status()
            payload = res.json()
            chart_error = (payload.get("chart") or {}).get("error")
            if chart_error:
                raise RuntimeError(chart_error.get("description") or chart_error.get("code") or "Yahoo chart error")
            break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(str(last_error or "Yahoo chart API unavailable"))

    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: List[Dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        try:
            close = closes[i]
            if close is None:
                continue
            bars.append({
                "time": datetime.fromtimestamp(int(ts)).isoformat(),
                "open": round(float(opens[i] if opens[i] is not None else close), 4),
                "high": round(float(highs[i] if highs[i] is not None else close), 4),
                "low": round(float(lows[i] if lows[i] is not None else close), 4),
                "close": round(float(close), 4),
                "volume": int(volumes[i]) if i < len(volumes) and volumes[i] is not None else None,
            })
        except (IndexError, TypeError, ValueError):
            continue
    return bars


def _get_stale_cache(cache_key: str) -> Dict[str, Any]:
    """Return the latest cache row regardless of TTL for graceful UI fallback."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT result_json FROM tool_result_cache
               WHERE tool_name = ? AND cache_key = ?""",
            ("price_history", cache_key),
        ).fetchone()
        if not row:
            return {}
        import json
        data = json.loads(row["result_json"])
        data["stale"] = True
        return data
    finally:
        conn.close()


def _compute_overlays(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Server-computed overlay series aligned to bars: MA20, MA50, Bollinger, VWAP, RSI, MACD.

    Each series is a list the same length as bars, with None where the window
    isn't yet full. Keeps the chart client thin and consistent with technicals.
    """
    import pandas as pd
    import numpy as np

    n = len(bars)
    if n == 0:
        return {
            "ma20": [], "ma50": [], "ma200": [],
            "bb_upper": [], "bb_lower": [],
            "vwap": [], "rsi": [],
            "macd": {"line": [], "signal": [], "histogram": []}
        }

    closes = pd.Series([b["close"] for b in bars])
    highs = pd.Series([b["high"] for b in bars])
    lows = pd.Series([b["low"] for b in bars])
    vols = pd.Series([b["volume"] or 0 for b in bars])

    # Moving averages
    ma20 = closes.rolling(20).mean()
    ma50 = closes.rolling(50).mean()
    ma200 = closes.rolling(200).mean()

    # Bollinger Bands
    std20 = closes.rolling(20).std()
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20

    # VWAP
    typical = (highs + lows + closes) / 3.0
    cum_pv = (typical * vols).cumsum()
    cum_v = vols.cumsum()
    vwap = cum_pv / cum_v

    # RSI (14)
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    gain_roll = gain.rolling(window=14).mean()
    loss_roll = loss.rolling(window=14).mean()
    rs = gain_roll / loss_roll
    rsi = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    def sanitize(series) -> List:
        res = []
        for val in series:
            if pd.isna(val) or np.isinf(val):
                res.append(None)
            else:
                res.append(round(float(val), 4))
        return res

    return {
        "ma20": sanitize(ma20),
        "ma50": sanitize(ma50),
        "ma200": sanitize(ma200),
        "bb_upper": sanitize(bb_upper),
        "bb_lower": sanitize(bb_lower),
        "vwap": sanitize(vwap),
        "rsi": sanitize(rsi),
        "macd": {
            "line": sanitize(macd_line),
            "signal": sanitize(signal_line),
            "histogram": sanitize(macd_hist)
        }
    }



class PriceHistoryTool(Tool):
    name = "price_history"
    description = (
        "OHLCV candlestick bars for a US-listed ticker over a given range and "
        "interval, via yfinance. Ranges: 1d, 5d, 1m, 3m, 1y, 5y."
    )
    cache_ttl_seconds = 60 * 60
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "range": {
                    "type": "string",
                    "enum": list(RANGE_TO_YF.keys()),
                    "description": "Lookback window (default 1y)",
                },
                "interval": {
                    "type": "string",
                    "description": "Bar interval override (e.g. 1m, 5m, 1d)",
                },
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, range: str = "1y", interval: str = "", **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        rng = range if range in RANGE_TO_YF else "1y"
        yf_period, default_interval = RANGE_TO_YF[rng]
        yf_interval = interval or default_interval

        # Polygon upgrade path (documented data tier): intraday minute ticks.
        # Gated on key presence so the free tier degrades to yfinance silently.
        if os.environ.get("POLYGON_API_KEY", "").strip() and yf_interval.endswith("m"):
            pass  # reserved for Polygon fetcher; yfinance handles free tier below

        cache_key = f"{_CACHE_VERSION}|{ticker}|{rng}|{yf_interval}"
        ttl = _TTL_BY_RANGE.get(rng, self.cache_ttl_seconds)
        cached = get_tool_cache(self.name, cache_key, ttl)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(ticker, cached=True),
                confidence="high", cached=True,
            )

        fetch_error = None
        try:
            import yfinance as yf
            hist = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval, auto_adjust=True)
        except Exception as e:
            hist = None
            fetch_error = e

        if hist is None or hist.empty:
            try:
                bars = _fetch_yahoo_chart(ticker, yf_period, yf_interval)
                if bars:
                    data = {
                        "ticker": ticker,
                        "range": rng,
                        "interval": yf_interval,
                        "bars": bars,
                        "overlays": _compute_overlays(bars),
                        "as_of": datetime.now().isoformat(),
                        "fallback": "yahoo_chart_api",
                    }
                    save_tool_cache(self.name, cache_key, data)
                    return ToolResult(
                        tool_name=self.name, data=data,
                        sources=_build_sources(ticker, cached=False, fallback=True),
                        confidence="medium" if len(bars) >= 20 else "low",
                    )
            except Exception as fallback_error:
                fetch_error = fetch_error or fallback_error

            stale = _get_stale_cache(cache_key)
            if stale.get("bars"):
                stale.setdefault("warning", "Live price refresh failed; showing cached chart.")
                return ToolResult(
                    tool_name=self.name, data=stale,
                    sources=_build_sources(ticker, cached=True),
                    confidence="medium", cached=True,
                )
            return ToolResult(
                tool_name=self.name, data={"bars": [], "ticker": ticker, "range": rng},
                sources=[], confidence="low",
                error=str(fetch_error or "No price history available"),
            )

        bars = _bars_from_history(hist)
        data = {
            "ticker": ticker,
            "range": rng,
            "interval": yf_interval,
            "bars": bars,
            "overlays": _compute_overlays(bars),
            "as_of": datetime.now().isoformat(),
        }
        save_tool_cache(self.name, cache_key, data)
        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(ticker, cached=False),
            confidence="high" if len(bars) >= 20 else "medium",
        )


def _build_sources(ticker: str, cached: bool, fallback: bool = False) -> List[Source]:
    now = datetime.now().isoformat()
    return [Source(
        tool="price_history", field="bars",
        fetched_at=now,
        url=f"https://finance.yahoo.com/quote/{ticker}/history",
        note=(
            "Yahoo Finance chart API fallback" if fallback else
            "yfinance history" + (" (cached)" if cached else "")
        ),
    )]


register(PriceHistoryTool())

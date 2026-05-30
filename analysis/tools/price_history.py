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
from db import get_tool_cache, save_tool_cache


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
            "ma20": [], "ma50": [],
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

        try:
            import yfinance as yf
            hist = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval, auto_adjust=True)
        except Exception as e:
            return ToolResult(
                tool_name=self.name, data={"bars": []},
                error=str(e), confidence="low",
            )

        if hist is None or hist.empty:
            return ToolResult(
                tool_name=self.name, data={"bars": [], "ticker": ticker, "range": rng},
                sources=[], confidence="low",
                error="No price history available",
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


def _build_sources(ticker: str, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    return [Source(
        tool="price_history", field="bars",
        fetched_at=now,
        url=f"https://finance.yahoo.com/quote/{ticker}/history",
        note="yfinance history" + (" (cached)" if cached else ""),
    )]


register(PriceHistoryTool())

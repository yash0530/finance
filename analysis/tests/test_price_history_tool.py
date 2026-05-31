"""
Tests for tools.price_history — OHLCV bars for the chart endpoint.

yfinance is mocked via monkeypatch so these run offline.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import db
from tools import ToolResult


@pytest.fixture(autouse=True)
def _wipe_cache():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache")
        conn.commit()
    finally:
        conn.close()
    yield


def _ohlc(n=30):
    idx = pd.date_range(end="2026-05-20", periods=n, freq="D")
    base = [100 + i for i in range(n)]
    return pd.DataFrame(
        {
            "Open": base,
            "High": [b + 2 for b in base],
            "Low": [b - 2 for b in base],
            "Close": [b + 1 for b in base],
            "Volume": [1_000_000 + i for i in range(n)],
        },
        index=idx,
    )


def _fake_yf(df, capture=None):
    class _Ticker:
        def __init__(self, t):
            pass

        def history(self, period="1y", interval="1d", auto_adjust=True):
            if capture is not None:
                capture["period"] = period
                capture["interval"] = interval
            return df

    return SimpleNamespace(Ticker=_Ticker)


def _fake_yf_error(message="Too Many Requests. Rate limited. Try after a while."):
    class _Ticker:
        def __init__(self, t):
            pass

        def history(self, period="1y", interval="1d", auto_adjust=True):
            raise RuntimeError(message)

    return SimpleNamespace(Ticker=_Ticker)


def _chart_bars(n=30):
    return [
        {
            "time": f"2026-05-{day:02d}T00:00:00",
            "open": 100 + day,
            "high": 102 + day,
            "low": 98 + day,
            "close": 101 + day,
            "volume": 1_000_000 + day,
        }
        for day in range(1, n + 1)
    ]


def test_price_history_returns_bars(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(_ohlc(30)))
    from tools.price_history import PriceHistoryTool
    result = PriceHistoryTool().execute(ticker="NVDA", range="1y")
    assert isinstance(result, ToolResult)
    assert result.is_ok()
    bars = result.data["bars"]
    assert len(bars) == 30
    first = bars[0]
    assert set(first.keys()) == {"time", "open", "high", "low", "close", "volume"}
    assert result.data["range"] == "1y"
    assert result.confidence == "high"


def test_price_history_maps_range_to_interval(monkeypatch):
    capture = {}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(_ohlc(10), capture))
    from tools.price_history import PriceHistoryTool
    PriceHistoryTool().execute(ticker="NVDA", range="1d")
    assert capture["period"] == "1d"
    assert capture["interval"] == "5m"


def test_price_history_interval_override(monkeypatch):
    capture = {}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(_ohlc(10), capture))
    from tools.price_history import PriceHistoryTool
    PriceHistoryTool().execute(ticker="NVDA", range="1y", interval="1wk")
    assert capture["interval"] == "1wk"


def test_price_history_empty_degrades(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(pd.DataFrame()))
    from tools.price_history import PriceHistoryTool
    result = PriceHistoryTool().execute(ticker="ZZZZ", range="1y")
    assert isinstance(result, ToolResult)
    assert result.error is not None
    assert result.confidence == "low"
    assert result.data["bars"] == []


def test_price_history_unknown_range_defaults_to_1y(monkeypatch):
    capture = {}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(_ohlc(5), capture))
    from tools.price_history import PriceHistoryTool
    result = PriceHistoryTool().execute(ticker="NVDA", range="bogus")
    assert result.data["range"] == "1y"
    assert capture["period"] == "1y"


def test_price_history_includes_overlays(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(_ohlc(60)))
    from tools.price_history import PriceHistoryTool
    result = PriceHistoryTool().execute(ticker="NVDA", range="1y")
    assert result.is_ok()
    overlays = result.data["overlays"]
    assert set(overlays.keys()) == {"ma20", "ma50", "ma200", "bb_upper", "bb_lower", "vwap", "rsi", "macd"}
    # ma20 should be None for the first 19 bars, populated after.
    assert overlays["ma20"][0] is None
    assert overlays["ma20"][19] is not None
    assert overlays["ma50"][49] is not None
    # VWAP is defined from the first bar.
    assert overlays["vwap"][0] is not None
    # Bollinger upper >= lower where both populated.
    assert overlays["bb_upper"][25] >= overlays["bb_lower"][25]


def test_price_history_yahoo_chart_fallback_is_success(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf_error())
    monkeypatch.setattr("tools.price_history._fetch_yahoo_chart", lambda *args: _chart_bars(30))
    from tools.price_history import PriceHistoryTool

    result = PriceHistoryTool().execute(ticker="NVDA", range="1y")

    assert result.is_ok()
    assert result.error is None
    assert result.data["fallback"] == "yahoo_chart_api"
    assert len(result.data["bars"]) == 30


def test_price_history_stale_cache_is_success_when_live_fetch_fails(monkeypatch):
    from tools.price_history import PriceHistoryTool, _CACHE_VERSION

    cache_key = f"{_CACHE_VERSION}|NVDA|1y|1d"
    db.save_tool_cache("price_history", cache_key, {
        "ticker": "NVDA",
        "range": "1y",
        "interval": "1d",
        "bars": _chart_bars(30),
        "overlays": {},
    })
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE tool_result_cache SET fetched_at = ? WHERE tool_name = ? AND cache_key = ?",
            ("2020-01-01T00:00:00", "price_history", cache_key),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf_error())
    monkeypatch.setattr("tools.price_history._fetch_yahoo_chart", lambda *args: (_ for _ in ()).throw(RuntimeError("429")))

    result = PriceHistoryTool().execute(ticker="NVDA", range="1y")

    assert result.is_ok()
    assert result.error is None
    assert result.cached is True
    assert result.data["stale"] is True
    assert result.data["warning"] == "Live price refresh failed; showing cached chart."

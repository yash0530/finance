"""
Tests for tools.movers — batched quotes + top movers ranking.

yfinance is mocked via monkeypatch so these run offline.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

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


class _FastInfo:
    def __init__(self, last_price, previous_close, last_volume=1000, market_cap=None):
        self.last_price = last_price
        self.previous_close = previous_close
        self.last_volume = last_volume
        self.market_cap = market_cap


def _fake_yf(quotes):
    class _Ticker:
        def __init__(self, t):
            self._t = t.upper()

        @property
        def fast_info(self):
            fi = quotes.get(self._t)
            if fi is None:
                raise RuntimeError("no data")
            return fi

    return SimpleNamespace(Ticker=_Ticker)


def test_movers_ranks_gainers_and_losers(monkeypatch):
    quotes = {
        "AAA": _FastInfo(110, 100),   # +10%
        "BBB": _FastInfo(95, 100),    # -5%
        "CCC": _FastInfo(102, 100),   # +2%
        "DDD": _FastInfo(80, 100),    # -20%
    }
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))

    from tools.movers import MoversTool
    result = MoversTool().execute(tickers=["AAA", "BBB", "CCC", "DDD"], top_n=2)

    assert isinstance(result, ToolResult)
    assert result.is_ok()
    d = result.data
    assert d["resolved"] == 4
    assert d["gainers"][0]["ticker"] == "AAA"
    assert d["gainers"][0]["change_pct"] == pytest.approx(10.0)
    assert d["losers"][0]["ticker"] == "DDD"
    assert d["losers"][0]["change_pct"] == pytest.approx(-20.0)
    assert len(d["gainers"]) == 2
    assert any(s.field == "gainers/losers" for s in result.sources)


def test_movers_skips_unresolved_tickers(monkeypatch):
    quotes = {"AAA": _FastInfo(110, 100)}  # BBB will raise
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))

    from tools.movers import MoversTool
    result = MoversTool().execute(tickers=["AAA", "BBB"], top_n=10)
    assert result.is_ok()
    assert result.data["resolved"] == 1
    assert result.data["universe_size"] == 2


def test_movers_degrades_when_no_quotes(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({}))
    from tools.movers import MoversTool
    result = MoversTool().execute(tickers=["AAA", "BBB"])
    assert isinstance(result, ToolResult)
    assert result.error is not None
    assert result.confidence == "low"
    assert result.data["gainers"] == []


def test_movers_handles_zero_previous_close(monkeypatch):
    quotes = {"AAA": _FastInfo(110, 0), "BBB": _FastInfo(50, 40)}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))
    from tools.movers import MoversTool
    result = MoversTool().execute(tickers=["AAA", "BBB"])
    assert result.is_ok()
    assert result.data["resolved"] == 1
    assert result.data["gainers"][0]["ticker"] == "BBB"

"""
Tests for tools.quote_snapshot — shared Daily Scan quote spine.

yfinance is mocked via monkeypatch so these run offline.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import db


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


def setup_function():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache")
        conn.commit()
    finally:
        conn.close()


def test_quote_snapshot_fetches_and_caches(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({
        "AAA": _FastInfo(110, 100),
        "BBB": _FastInfo(95, 100),
    }))
    from tools.quote_snapshot import QuoteSnapshotTool

    first = QuoteSnapshotTool().execute(tickers=["AAA", "BBB"])
    assert first.error is None
    assert first.data["resolved_count"] == 2
    assert first.data["quotes"]["AAA"]["change_pct"] == 10.0

    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({}))
    second = QuoteSnapshotTool().execute(tickers=["AAA", "BBB"])
    assert second.cached is True
    assert second.data["quotes"]["BBB"]["change_pct"] == -5.0


def test_quote_snapshot_uses_stale_cache_when_expired_live_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({
        "AAA": _FastInfo(110, 100),
        "BBB": _FastInfo(95, 100),
    }))
    from tools.quote_snapshot import QuoteSnapshotTool

    first = QuoteSnapshotTool().execute(tickers=["AAA", "BBB"])
    assert first.error is None

    stale_at = (datetime.now() - timedelta(hours=1)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE tool_result_cache SET fetched_at = ? WHERE tool_name = ?",
            (stale_at, "quote_snapshot"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({}))
    second = QuoteSnapshotTool().execute(tickers=["AAA", "BBB"])
    assert second.error is None
    assert second.cached is True
    assert second.confidence == "low"
    assert second.data["stale"] is True
    assert second.data["quotes"]["AAA"]["price"] == 110

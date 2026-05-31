"""
Tests for tools.theme_heat — per-theme median move + leader/laggard.

yfinance is mocked; themes are seeded directly into the test DB.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import db
from tools import ToolResult


@pytest.fixture(autouse=True)
def _setup():
    conn = db.get_connection()
    try:
        for tbl in ("tool_result_cache", "theme_tickers", "themes"):
            conn.execute(f"DELETE FROM {tbl}")
        conn.commit()
    finally:
        conn.close()
    db.upsert_theme("ai", "AI Infra")
    db.add_theme_ticker("ai", "NVDA")
    db.add_theme_ticker("ai", "AMD")
    db.add_theme_ticker("ai", "AVGO")
    db.upsert_theme("mem", "Memory")
    db.add_theme_ticker("mem", "MU")
    yield


class _FastInfo:
    def __init__(self, last_price, previous_close):
        self.last_price = last_price
        self.previous_close = previous_close
        self.last_volume = 1000
        self.market_cap = None


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


def test_theme_heat_computes_median_and_extremes(monkeypatch):
    quotes = {
        "NVDA": _FastInfo(110, 100),  # +10
        "AMD": _FastInfo(102, 100),   # +2
        "AVGO": _FastInfo(94, 100),   # -6
        "MU": _FastInfo(105, 100),    # +5
    }
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))

    from tools.theme_heat import ThemeHeatTool
    result = ThemeHeatTool().execute()
    assert isinstance(result, ToolResult)
    assert result.is_ok()

    by_slug = {t["slug"]: t for t in result.data["themes"]}
    ai = by_slug["ai"]
    assert ai["resolved"] == 3
    assert ai["median_change_pct"] == pytest.approx(2.0)  # median of [10, 2, -6]
    assert ai["leader"]["ticker"] == "NVDA"
    assert ai["laggard"]["ticker"] == "AVGO"
    assert by_slug["mem"]["median_change_pct"] == pytest.approx(5.0)

    # Sorted by median desc → mem (5) before ai (2)
    assert result.data["themes"][0]["slug"] == "mem"


def test_theme_heat_handles_unresolved_theme(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({}))
    from tools.theme_heat import ThemeHeatTool
    result = ThemeHeatTool().execute()
    assert result.is_ok()
    for t in result.data["themes"]:
        assert t["resolved"] == 0
        assert t["median_change_pct"] is None
        assert t["leader"] is None


def test_theme_heat_uses_stale_cache_when_live_quotes_fail(monkeypatch):
    quotes = {
        "NVDA": _FastInfo(110, 100),
        "AMD": _FastInfo(102, 100),
        "AVGO": _FastInfo(94, 100),
        "MU": _FastInfo(105, 100),
    }
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))
    from tools.theme_heat import ThemeHeatTool
    first = ThemeHeatTool().execute()
    assert first.is_ok()

    stale_at = (datetime.now() - timedelta(hours=2)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE tool_result_cache SET fetched_at = ? WHERE tool_name = ?",
            (stale_at, "theme_heat"),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({}))
    second = ThemeHeatTool().execute()
    assert second.error is None
    assert second.cached is True
    assert second.confidence == "low"
    assert second.data["stale"] is True
    assert second.data["themes"][0]["slug"] == "mem"


def test_theme_heat_sp500_sectors(monkeypatch):
    monkeypatch.setattr(
        "tools.sp500_lookup.sp500_by_sector",
        lambda: {"Information Technology": ["NVDA", "AMD"], "Energy": ["XOM"]},
    )
    quotes = {
        "NVDA": _FastInfo(110, 100),  # +10
        "AMD": _FastInfo(90, 100),    # -10
        "XOM": _FastInfo(102, 100),   # +2
    }
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))

    from tools.theme_heat import ThemeHeatTool
    result = ThemeHeatTool().execute(universe="sp500-sectors")
    assert result.is_ok()
    assert result.data["universe"] == "sp500-sectors"
    by_name = {t["name"]: t for t in result.data["themes"]}
    assert "Information Technology" in by_name and "Energy" in by_name
    it = by_name["Information Technology"]
    assert it["leader"]["ticker"] == "NVDA"
    assert it["laggard"]["ticker"] == "AMD"


def test_theme_heat_no_themes_degrades(monkeypatch):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM theme_tickers")
        conn.execute("DELETE FROM themes")
        conn.commit()
    finally:
        conn.close()
    from tools.theme_heat import ThemeHeatTool
    result = ThemeHeatTool().execute()
    assert result.error is not None
    assert result.confidence == "low"

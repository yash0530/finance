"""
Tests for the Phase 1 Terminal endpoints: movers, news, watchlist CRUD, chart.

The underlying yfinance / news fetchers are monkeypatched so no network is hit.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import app as _app
import db
import sentiment_service


@pytest.fixture
def client():
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe():
    conn = db.get_connection()
    try:
        for tbl in ("tool_result_cache", "watchlist"):
            conn.execute(f"DELETE FROM {tbl}")
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


def test_movers_endpoint(client, monkeypatch):
    quotes = {"NVDA": _FastInfo(110, 100), "AMD": _FastInfo(90, 100)}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))
    res = client.get("/api/terminal/movers?universe=watchlist")
    assert res.status_code == 200
    # watchlist empty → universe empty → low confidence / no resolved
    body = res.get_json()
    assert "data" in body


def test_watchlist_crud_and_enrichment(client, monkeypatch):
    # Add two tickers
    assert client.post("/api/terminal/watchlist", json={"ticker": "nvda"}).status_code == 200
    assert client.post("/api/terminal/watchlist", json={"ticker": "AMD", "notes": "memory"}).status_code == 200

    quotes = {"NVDA": _FastInfo(110, 100), "AMD": _FastInfo(95, 100)}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))

    res = client.get("/api/terminal/watchlist")
    assert res.status_code == 200
    body = res.get_json()
    assert body["count"] == 2
    by_ticker = {i["ticker"]: i for i in body["items"]}
    assert by_ticker["NVDA"]["change_pct"] == pytest.approx(10.0)
    assert by_ticker["AMD"]["notes"] == "memory"

    # Delete one
    assert client.delete("/api/terminal/watchlist/NVDA").status_code == 200
    body = client.get("/api/terminal/watchlist").get_json()
    assert body["count"] == 1
    assert body["items"][0]["ticker"] == "AMD"


def test_watchlist_add_requires_ticker(client):
    res = client.post("/api/terminal/watchlist", json={})
    assert res.status_code == 400


def test_news_endpoint(client, monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "fake")
    monkeypatch.setattr(
        sentiment_service, "get_finnhub_news",
        lambda t, days_back=7: [{
            "headline": f"{t} ships chips", "summary": "", "url": f"http://x/{t}",
            "source": "Wire", "published_at": "2026-05-20",
        }],
    )
    res = client.get("/api/terminal/news?theme=NVDA&limit=10")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["count"] >= 1


def test_chart_endpoint(client, monkeypatch):
    idx = pd.date_range(end="2026-05-20", periods=10, freq="D")
    df = pd.DataFrame(
        {"Open": range(10), "High": range(10), "Low": range(10),
         "Close": range(10), "Volume": range(10)}, index=idx,
    )

    class _Ticker:
        def __init__(self, t):
            pass

        def history(self, period="1y", interval="1d", auto_adjust=True):
            return df

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_Ticker))
    res = client.get("/api/chart/NVDA?range=1m")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["ticker"] == "NVDA"
    assert len(body["data"]["bars"]) == 10

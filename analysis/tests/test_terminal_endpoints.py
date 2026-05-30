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


# ============================================================================
# Phase 2 endpoints: theme-heat, catalysts, flow, hypothesis, themes CRUD
# ============================================================================

@pytest.fixture
def _seed_theme():
    db.upsert_theme("ai", "AI Infra")
    db.add_theme_ticker("ai", "NVDA")
    db.add_theme_ticker("ai", "AMD")
    yield
    db.delete_theme("ai")


def test_theme_heat_endpoint(client, monkeypatch, _seed_theme):
    quotes = {"NVDA": _FastInfo(110, 100), "AMD": _FastInfo(95, 100)}
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(quotes))
    res = client.get("/api/terminal/theme-heat")
    assert res.status_code == 200
    body = res.get_json()
    by_slug = {t["slug"]: t for t in body["data"]["themes"]}
    assert "ai" in by_slug
    assert by_slug["ai"]["leader"]["ticker"] == "NVDA"


def test_flow_endpoint_degrades_without_uw_key(client, monkeypatch):
    monkeypatch.delenv("UNUSUAL_WHALES_API_KEY", raising=False)
    res = client.get("/api/terminal/flow?ticker=NVDA")
    assert res.status_code == 200
    body = res.get_json()
    assert body["degraded"] is True
    assert "reason" in body


def test_hypothesis_endpoint_requires_ticker(client):
    res = client.post("/api/terminal/hypothesis", json={})
    assert res.status_code == 400


def test_hypothesis_endpoint_caches(client, monkeypatch):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM hypotheses_cache")
        conn.commit()
    finally:
        conn.close()

    calls = {"n": 0}

    def fake_run(ticker):
        calls["n"] += 1
        return {
            "ticker": ticker, "why_md": "because reasons [news_tape]",
            "stance": "bullish", "evidence_refs": ["news_tape"], "cost_usd": 0.05,
        }

    import agent_loop
    monkeypatch.setattr(agent_loop, "run_quick_take", fake_run)

    r1 = client.post("/api/terminal/hypothesis", json={"ticker": "NVDA"}).get_json()
    assert r1["cached"] is False
    assert r1["why_md"]
    r2 = client.post("/api/terminal/hypothesis", json={"ticker": "NVDA"}).get_json()
    assert r2["cached"] is True
    assert calls["n"] == 1  # second call served from cache


def test_themes_crud_endpoints(client):
    # Create
    assert client.post("/api/themes", json={"slug": "tst", "name": "Test", "tickers": ["NVDA"]}).status_code == 200
    # List
    body = client.get("/api/themes").get_json()
    assert any(t["slug"] == "tst" for t in body["themes"])
    # Add ticker
    assert client.post("/api/themes/tst/tickers", json={"ticker": "AMD"}).status_code == 200
    detail = client.get("/api/themes/tst/tickers").get_json()
    assert {t["ticker"] for t in detail["tickers"]} == {"NVDA", "AMD"}
    # by-ticker reverse lookup
    rev = client.get("/api/themes/by-ticker/NVDA").get_json()
    assert any(t["slug"] == "tst" for t in rev["themes"])
    # Remove ticker
    assert client.delete("/api/themes/tst/tickers/NVDA").status_code == 200
    detail = client.get("/api/themes/tst/tickers").get_json()
    assert {t["ticker"] for t in detail["tickers"]} == {"AMD"}
    # Delete theme
    assert client.delete("/api/themes/tst").status_code == 200
    body = client.get("/api/themes").get_json()
    assert not any(t["slug"] == "tst" for t in body["themes"])

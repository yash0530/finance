"""
Tests for Phase 3 Stock View endpoints + relative_strength_vs_spy + EDGAR
filings list helper.

yfinance / SEC are mocked so these run offline.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import app as _app
import db


@pytest.fixture
def client():
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _wipe():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache")
        conn.commit()
    finally:
        conn.close()
    yield


def _hist(prices):
    idx = pd.date_range(end="2026-05-20", periods=len(prices), freq="B")
    return pd.DataFrame({
        "Open": prices, "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices], "Close": prices,
        "Volume": [1_000_000] * len(prices),
    }, index=idx)


def test_relative_strength_vs_spy_computed(monkeypatch):
    """Ticker that doubled while SPY stayed flat → RS ~2.0."""
    ticker_prices = [50.0] * 251 + [100.0]   # 2x over the window
    spy_prices = [400.0] * 252               # flat

    class _Ticker:
        def __init__(self, sym):
            self.sym = sym.upper()

        def history(self, period="1y", auto_adjust=True):
            return _hist(spy_prices if self.sym == "SPY" else ticker_prices)

    import research_engine
    monkeypatch.setattr(research_engine, "yf", SimpleNamespace(Ticker=_Ticker))

    data = research_engine.fetch_technicals("NVDA")
    assert "relative_strength_vs_spy" in data
    assert data["relative_strength_vs_spy"] == pytest.approx(2.0, abs=0.05)


def test_relative_strength_none_for_spy_itself(monkeypatch):
    class _Ticker:
        def __init__(self, sym):
            pass
        def history(self, period="1y", auto_adjust=True):
            return _hist([400.0] * 252)

    import research_engine
    monkeypatch.setattr(research_engine, "yf", SimpleNamespace(Ticker=_Ticker))
    data = research_engine.fetch_technicals("SPY")
    assert data["relative_strength_vs_spy"] is None


def test_list_recent_filings(monkeypatch):
    import edgar_service

    monkeypatch.setattr(edgar_service, "get_cik", lambda t: "0001045810")

    class _Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"filings": {"recent": {
                "form": ["10-K", "8-K", "4"],
                "accessionNumber": ["0001-23-000001", "0001-23-000002", "0001-23-000003"],
                "filingDate": ["2026-02-20", "2026-03-15", "2026-04-01"],
                "primaryDocument": ["nvda-10k.htm", "nvda-8k.htm", "form4.xml"],
            }}}

    monkeypatch.setattr(edgar_service, "_rate_limited_get", lambda *a, **k: _Resp())
    filings = edgar_service.list_recent_filings("NVDA", limit=10)
    assert len(filings) == 3
    assert filings[0]["form"] == "10-K"
    assert filings[0]["url"].startswith("https://www.sec.gov/Archives/edgar/data/")


def test_stock_filings_endpoint(client, monkeypatch):
    import edgar_service
    monkeypatch.setattr(edgar_service, "list_recent_filings",
                        lambda t, limit=15: [{"form": "10-K", "filing_date": "2026-02-20", "url": "http://x", "accession": "a"}])
    res = client.get("/api/stock/NVDA/filings")
    assert res.status_code == 200
    body = res.get_json()
    assert body["count"] == 1
    assert body["filings"][0]["form"] == "10-K"


def test_stock_header_endpoint(client, monkeypatch):
    import research_engine
    monkeypatch.setattr(research_engine, "fetch_fundamentals",
                        lambda t: {"current_price": 100.0, "market_cap": 1e12, "analyst_target": 120.0})
    res = client.get("/api/stock/NVDA/header")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["current_price"] == 100.0

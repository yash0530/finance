"""
Tests for the Phase 1 Terminal endpoints: movers, news, watchlist CRUD, chart.

The underlying yfinance / news fetchers are monkeypatched so no network is hit.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
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
        for tbl in ("tool_result_cache", "watchlist", "catalysts"):
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


def test_catalysts_endpoint_dedupes_market_wide_events(client, monkeypatch, _seed_theme):
    import tools

    class _NoopTool:
        def execute(self, **kwargs):
            return SimpleNamespace()

    monkeypatch.setattr(tools, "get_tool", lambda name: _NoopTool())
    event_date = (date.today() + timedelta(days=2)).isoformat()
    for ticker in ("NVDA", "AMD", "MARKET"):
        db.upsert_catalyst(ticker, "NFP", event_date, "Payrolls", "static_calendar")

    res = client.get("/api/terminal/catalysts?days=7")
    assert res.status_code == 200
    body = res.get_json()
    rows = [r for r in body["items"] if r["event_type"] == "NFP" and r["event_date"] == event_date]
    assert len(rows) == 1
    assert rows[0]["ticker"] == "MARKET"
    assert rows[0]["market_wide"] is True


def test_terminal_snapshot_returns_one_daily_scan_envelope(client, monkeypatch, _seed_theme):
    monkeypatch.setattr(_app, "_terminal_universe", lambda: ["NVDA", "AMD"])
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf({
        "NVDA": _FastInfo(110, 100),
        "AMD": _FastInfo(95, 100),
    }))
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setattr(
        sentiment_service,
        "get_yfinance_news",
        lambda t: [{
            "headline": f"{t} morning read",
            "summary": "",
            "url": f"http://x/{t}",
            "source": "Wire",
            "published_at": "2026-05-30",
        }],
    )

    res = client.get("/api/terminal/snapshot?news_universe_limit=2")
    assert res.status_code == 200
    body = res.get_json()
    assert body["universe"]["count"] == 2
    assert body["panels"]["quotes"]["data"]["resolved_count"] == 2
    assert body["panels"]["movers"]["data"]["gainers"][0]["ticker"] == "NVDA"
    assert body["panels"]["flow"]["status"] == "degraded"
    assert len(body["health"]) >= 5


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


def test_data_tier_reports_sp500_snapshot(client, tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    cache_path.write_text('{"timestamp":"2026-05-20T00:00:00","data":[{"ticker":"AAPL"}]}')
    import tools.sp500_refresh as refresh
    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)

    body = client.get("/api/settings/data-tier").get_json()
    assert body["sp500_snapshot"]["timestamp"] == "2026-05-20T00:00:00"
    assert body["sp500_snapshot"]["row_count"] == 1


def test_refresh_sp500_endpoint(client, monkeypatch):
    class _Result:
        error = None
        def to_dict(self):
            return {"tool_name": "sp500_refresh", "data": {"row_count": 1}}

    class _Tool:
        def execute(self, **args):
            assert args == {}
            return _Result()

    import tools
    monkeypatch.setattr(tools, "get_tool", lambda name: _Tool())

    res = client.post("/api/market/refresh-sp500")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True
    body = client.get("/api/themes").get_json()
    assert not any(t["slug"] == "tst" for t in body["themes"])


def test_market_sp500_snapshot_endpoints(client, monkeypatch):
    rows = [
        {
            "ticker": "AAA", "company_name": "Alpha AI", "sector": "Information Technology",
            "current_price": 100, "current_price_fmt": "$100.00",
            "market_cap": 500_000_000_000, "market_cap_fmt": "$500.00B",
            "forward_pe": 20, "trailing_pe": 30, "pe_ratio": 1.5,
            "profit_margin": 0.22, "revenue_growth": 0.25, "revenue_growth_fmt": "25.00%",
            "year_change": 0.35, "year_change_fmt": "35.00%", "beta": 1.2,
            "dividend_yield": 0.01,
        },
        {
            "ticker": "BBB", "company_name": "Beta Bank", "sector": "Financials",
            "current_price": 50, "current_price_fmt": "$50.00",
            "market_cap": 50_000_000_000, "market_cap_fmt": "$50.00B",
            "forward_pe": 10, "trailing_pe": 14, "pe_ratio": 1.4,
            "profit_margin": 0.12, "revenue_growth": 0.04, "revenue_growth_fmt": "4.00%",
            "year_change": -0.20, "year_change_fmt": "-20.00%", "beta": 0.7,
            "dividend_yield": 0.04,
        },
    ]
    monkeypatch.setattr(_app, "_sp500_rows", lambda: rows)
    monkeypatch.setattr(_app, "_sp500_status", lambda: {"timestamp": "2026-05-20T00:00:00", "row_count": 2})

    stats = client.get("/api/market/sp500/stats").get_json()
    assert stats["total_companies"] == 2
    assert stats["top_by_market_cap"][0]["ticker"] == "AAA"

    sectors = client.get("/api/market/sp500/sectors").get_json()
    assert {s["name"] for s in sectors["data"]} == {"Financials", "Information Technology"}

    search = client.get("/api/market/sp500/search?q=bank").get_json()
    assert search["count"] == 1
    assert search["data"][0]["ticker"] == "BBB"


def test_market_sp500_spotlight_category(client, monkeypatch):
    rows = [
        {
            "ticker": "AAA", "company_name": "Alpha AI", "sector": "Information Technology",
            "current_price_fmt": "$100.00", "market_cap": 500_000_000_000,
            "market_cap_fmt": "$500.00B", "forward_pe": 20, "trailing_pe": 30,
            "pe_ratio": 1.5, "profit_margin": 0.22, "revenue_growth": 0.25,
            "year_change": 0.35, "beta": 1.2, "dividend_yield": 0.01,
        },
        {
            "ticker": "BBB", "company_name": "Beta Bank", "sector": "Financials",
            "current_price_fmt": "$50.00", "market_cap": 50_000_000_000,
            "market_cap_fmt": "$50.00B", "forward_pe": 10, "trailing_pe": 14,
            "pe_ratio": 1.4, "profit_margin": 0.12, "revenue_growth": 0.04,
            "year_change": -0.20, "beta": 0.7, "dividend_yield": 0.04,
        },
    ]
    monkeypatch.setattr(_app, "_sp500_rows", lambda: rows)

    spotlight = client.get("/api/market/sp500/spotlight").get_json()
    assert spotlight["growth_stocks"]["companies"][0]["ticker"] == "AAA"

    category = client.get("/api/market/sp500/spotlight/low_volatility").get_json()
    assert category["count"] == 1
    assert category["companies"][0]["ticker"] == "BBB"


def test_library_memos_endpoint(client):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM living_memo")
        conn.commit()
    finally:
        conn.close()
    db.save_living_memo(
        ticker="NVDA", content_md="# memo", content_json={"identity": {"content_md": "x"}},
        delta_summary="init",
    )
    res = client.get("/api/library/memos")
    assert res.status_code == 200
    body = res.get_json()
    assert any(m["ticker"] == "NVDA" for m in body["memos"])


def test_console_run_requires_command(client):
    res = client.post("/api/console/run", json={})
    assert res.status_code == 400


def test_console_run_streams_unknown_command(client):
    res = client.post("/api/console/run", json={"command": "/bogus NVDA"})
    assert res.status_code == 200
    text = res.get_data(as_text=True)
    assert "console_start" in text
    assert "console_error" in text


def test_data_tier_endpoint_free_default(client, monkeypatch):
    for k in ("FMP_API_KEY", "UNUSUAL_WHALES_API_KEY", "POLYGON_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    res = client.get("/api/settings/data-tier")
    assert res.status_code == 200
    tiers = {t["id"]: t for t in res.get_json()["tiers"]}
    assert tiers["free"]["active"] is True
    assert tiers["uw"]["active"] is False
    assert tiers["polygon"]["active"] is False


def test_data_tier_endpoint_reflects_env(client, monkeypatch):
    monkeypatch.setenv("UNUSUAL_WHALES_API_KEY", "fake")
    res = client.get("/api/settings/data-tier")
    tiers = {t["id"]: t for t in res.get_json()["tiers"]}
    assert tiers["uw"]["active"] is True
    # Secret value is never returned.
    assert "fake" not in res.get_data(as_text=True)


def test_dashboard_layout_roundtrip(client):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM dashboard_layout")
        conn.commit()
    finally:
        conn.close()

    order = ["news-tape", "movers", "flow"]
    assert client.post("/api/dashboard/layout", json={"layout": order}).status_code == 200
    body = client.get("/api/dashboard/layout").get_json()
    assert body["layout"] == order


def test_dashboard_layout_requires_layout(client):
    res = client.post("/api/dashboard/layout", json={})
    assert res.status_code == 400

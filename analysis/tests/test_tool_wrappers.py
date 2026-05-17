"""
Tests for Tool wrappers around core services.

Each underlying function is monkey-patched so tests never hit the network,
LLM, or external APIs. We verify:
  - happy path: ToolResult.is_ok(), expected data fields, sources, tool_name
  - error path: ToolResult.error is set, is_ok() is False
  - caching: a second call returns cached=True without re-invoking the fn
"""

import pytest

import db
import tools as tool_pkg


# ── Cache reset (shared) ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_cache():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache")
        conn.commit()
    finally:
        conn.close()
    yield


# ── financial_trends ────────────────────────────────────────────────────

def test_financial_trends_happy(monkeypatch):
    fake = {
        "quarter_count": 8,
        "quarters": [
            {"date": "2024-03-31", "quarter_label": "Q1 2024", "revenue": 1000},
            {"date": "2024-06-30", "quarter_label": "Q2 2024", "revenue": 1100},
        ],
        "signals": {"revenue_trend": {"direction": "expanding"}},
    }
    import research_engine
    calls = {"n": 0}

    def fake_fetch(ticker):
        calls["n"] += 1
        return fake

    monkeypatch.setattr(research_engine, "fetch_financial_trends", fake_fetch)

    tool = tool_pkg.get_tool("financial_trends")
    r1 = tool.execute(ticker="nvda")
    assert r1.is_ok()
    assert r1.tool_name == "financial_trends"
    assert r1.data["quarter_count"] == 8
    assert len(r1.sources) >= 1
    assert all(s.tool == "financial_trends" for s in r1.sources)
    assert r1.cached is False
    assert calls["n"] == 1

    # Cache hit on second call
    r2 = tool.execute(ticker="NVDA")
    assert r2.is_ok()
    assert r2.cached is True
    assert calls["n"] == 1  # underlying fn not called again


def test_financial_trends_error(monkeypatch):
    import research_engine
    monkeypatch.setattr(
        research_engine, "fetch_financial_trends",
        lambda t: {"error": "no data", "quarters": [], "signals": {}},
    )
    tool = tool_pkg.get_tool("financial_trends")
    r = tool.execute(ticker="ZZZZ")
    assert not r.is_ok()
    assert r.error == "no data"


# ── technicals ──────────────────────────────────────────────────────────

def test_technicals_happy(monkeypatch):
    fake = {
        "current_price": 100.0,
        "ma_50": 95.0,
        "ma_200": 90.0,
        "rsi": 55.0,
        "macd": {"macd": 0.5, "signal": 0.3, "histogram": 0.2, "signal_label": "bullish"},
        "bollinger": {"upper": 110, "middle": 100, "lower": 90, "position": 0.5},
        "year_return_pct": 25.0,
        "annualized_volatility_pct": 22.0,
        "patterns": [{"type": "double_bottom", "name": "Double Bottom", "signal": "bullish", "confidence": 0.8}],
        "data_points": 252,
        "golden_cross": True,
        "above_50ma": True,
        "above_200ma": True,
        "rsi_signal": "neutral",
    }
    import research_engine
    calls = {"n": 0}

    def fake_fetch(ticker, history_data=None):
        calls["n"] += 1
        return fake

    monkeypatch.setattr(research_engine, "fetch_technicals", fake_fetch)

    tool = tool_pkg.get_tool("technicals")
    r1 = tool.execute(ticker="NVDA")
    assert r1.is_ok()
    assert r1.tool_name == "technicals"
    assert r1.data["rsi"] == 55.0
    fields = {s.field for s in r1.sources}
    # Indicator-level sources
    assert "rsi" in fields
    assert "macd" in fields
    assert "ma_50" in fields
    assert "ma_200" in fields
    # Pattern source
    assert any(f.startswith("patterns:") for f in fields)
    assert r1.cached is False

    r2 = tool.execute(ticker="NVDA")
    assert r2.cached is True
    assert calls["n"] == 1


def test_technicals_error(monkeypatch):
    import research_engine
    monkeypatch.setattr(
        research_engine, "fetch_technicals",
        lambda t, history_data=None: {"error": "no history"},
    )
    tool = tool_pkg.get_tool("technicals")
    r = tool.execute(ticker="ZZZZ")
    assert not r.is_ok()
    assert "no history" in r.error


# ── dcf_valuation ───────────────────────────────────────────────────────

def test_dcf_valuation_happy_with_inputs(monkeypatch):
    fake_dcf = {
        "base_case": 150.0,
        "bull_case": 200.0,
        "bear_case": 100.0,
        "current_price": 120.0,
        "margin_of_safety_pct": 20.0,
        "implied_growth_rate": 10.0,
        "verdict": "Undervalued",
        "inputs": {"fcf_base": 1e10, "shares": 1e9, "discount_rate": 0.09},
    }
    import research_engine
    calls = {"n": 0}

    def fake_compute(ticker, fundamentals, trends):
        calls["n"] += 1
        return fake_dcf

    monkeypatch.setattr(research_engine, "compute_intrinsic_value", fake_compute)

    tool = tool_pkg.get_tool("dcf_valuation")
    r1 = tool.execute(
        ticker="NVDA",
        fundamentals_data={"current_price": 120.0, "is_etf": False},
        trends_data={"quarters": [], "signals": {}},
    )
    assert r1.is_ok()
    assert r1.tool_name == "dcf_valuation"
    assert r1.data["verdict"] == "Undervalued"
    fields = {s.field for s in r1.sources}
    assert "base_case" in fields and "bull_case" in fields and "bear_case" in fields
    assert r1.cached is False
    assert calls["n"] == 1

    r2 = tool.execute(
        ticker="NVDA",
        fundamentals_data={"current_price": 120.0, "is_etf": False},
        trends_data={"quarters": [], "signals": {}},
    )
    assert r2.cached is True
    assert calls["n"] == 1


def test_dcf_valuation_error(monkeypatch):
    import research_engine
    monkeypatch.setattr(
        research_engine, "compute_intrinsic_value",
        lambda t, f, tr: {"error": "Insufficient FCF data"},
    )
    tool = tool_pkg.get_tool("dcf_valuation")
    r = tool.execute(
        ticker="ZZZZ",
        fundamentals_data={"is_etf": False},
        trends_data={},
    )
    assert not r.is_ok()
    assert "Insufficient FCF" in r.error


# ── peer_compare ────────────────────────────────────────────────────────

def test_peer_compare_happy(monkeypatch):
    fake = {"sector": "Technology", "average_pe": 32.5, "average_ps": 6.2, "average_pb": 7.8}
    import research_engine
    calls = {"n": 0}

    def fake_fn(ticker, sector):
        calls["n"] += 1
        return fake

    monkeypatch.setattr(research_engine, "get_peer_valuation", fake_fn)

    tool = tool_pkg.get_tool("peer_compare")
    r1 = tool.execute(ticker="NVDA", sector="Technology")
    assert r1.is_ok()
    assert r1.tool_name == "peer_compare"
    assert r1.data["average_pe"] == 32.5
    fields = {s.field for s in r1.sources}
    assert "average_pe" in fields and "average_ps" in fields and "average_pb" in fields
    assert r1.cached is False

    r2 = tool.execute(ticker="NVDA", sector="Technology")
    assert r2.cached is True
    assert calls["n"] == 1

    # Different sector → different cache key → re-invokes
    r3 = tool.execute(ticker="NVDA", sector="Healthcare")
    assert r3.cached is False
    assert calls["n"] == 2


def test_peer_compare_error(monkeypatch):
    import research_engine
    monkeypatch.setattr(research_engine, "get_peer_valuation", lambda t, s: {})
    tool = tool_pkg.get_tool("peer_compare")
    r = tool.execute(ticker="NVDA", sector="Technology")
    assert not r.is_ok()
    assert r.error


# ── sentiment ───────────────────────────────────────────────────────────

def test_sentiment_happy(monkeypatch):
    fake = {
        "composite_score": 7.2,
        "label": "bullish",
        "news_score": 7.0,
        "analyst_score": 8.0,
        "reddit_score": 6.5,
        "analyst_rating": "Buy",
        "analyst_target": 150.0,
        "analyst_count": 25,
        "reddit_mentions": 12,
        "reddit_available": True,
        "top_headlines": ["NVDA beats earnings", "Analysts raise targets"],
        "sources_used": ["news", "analyst", "reddit"],
    }
    import sentiment_service
    calls = {"n": 0}

    def fake_fn(ticker):
        calls["n"] += 1
        return fake

    monkeypatch.setattr(sentiment_service, "get_composite_sentiment", fake_fn)

    tool = tool_pkg.get_tool("sentiment")
    r1 = tool.execute(ticker="NVDA")
    assert r1.is_ok()
    assert r1.tool_name == "sentiment"
    assert r1.data["composite_score"] == 7.2
    fields = {s.field for s in r1.sources}
    # News, analyst, reddit sources should all be represented
    assert "news_score" in fields
    assert "analyst_score" in fields
    assert "reddit_score" in fields
    # Headlines
    assert "headline" in fields

    # Sentiment is NOT cached at the tool layer (cache_ttl_seconds == 0)
    # → a second call always re-invokes the underlying fn
    r2 = tool.execute(ticker="NVDA")
    assert r2.is_ok()
    assert r2.cached is False
    assert calls["n"] == 2


def test_sentiment_error(monkeypatch):
    import sentiment_service

    def boom(ticker):
        raise RuntimeError("finnhub down")

    monkeypatch.setattr(sentiment_service, "get_composite_sentiment", boom)
    tool = tool_pkg.get_tool("sentiment")
    r = tool.execute(ticker="NVDA")
    assert not r.is_ok()
    assert "finnhub down" in r.error


# ── edgar_filings ───────────────────────────────────────────────────────

def test_edgar_filings_happy(monkeypatch):
    fake = {
        "available": True,
        "filing_date": "2025-02-20",
        "form_type": "10-K",
        "business": "- Designs GPUs.\n- Sells to data centers.",
        "risks": "- Concentrated customer base.\n- Export controls.",
        "mda": "- Revenue grew 75% YoY.\n- Gross margin expanded.",
    }
    import edgar_service
    calls = {"n": 0}

    def fake_fn(ticker, form_type="10-K"):
        calls["n"] += 1
        return fake

    monkeypatch.setattr(edgar_service, "summarize_filing", fake_fn)

    tool = tool_pkg.get_tool("edgar_filings")
    r1 = tool.execute(ticker="NVDA")
    assert r1.is_ok()
    assert r1.tool_name == "edgar_filings"
    assert r1.data["available"] is True
    fields = {s.field for s in r1.sources}
    assert "business" in fields and "risks" in fields and "mda" in fields
    # All section sources should carry a URL (filing URL fallback uses SEC)
    assert all(s.url for s in r1.sources)
    assert r1.cached is False
    assert calls["n"] == 1

    r2 = tool.execute(ticker="NVDA")
    assert r2.cached is True
    assert calls["n"] == 1


def test_edgar_filings_error(monkeypatch):
    import edgar_service
    monkeypatch.setattr(
        edgar_service, "summarize_filing",
        lambda t, form_type="10-K": {
            "business": "", "risks": "", "mda": "",
            "error": "Could not fetch 10-K filing for ZZZZ",
            "available": False,
        },
    )
    tool = tool_pkg.get_tool("edgar_filings")
    r = tool.execute(ticker="ZZZZ")
    assert not r.is_ok()
    assert "Could not fetch" in r.error

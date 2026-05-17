"""
Phase 1 market-data tool tests. All external HTTP / yfinance calls are mocked.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import pytest


# -----------------------------------------------------------------------------
# Common cache cleanup so tests don't pollute each other
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_caches():
    import db
    conn = db.get_connection()
    try:
        for tbl in (
            "tool_result_cache", "insider_trades_cache",
            "institutional_holdings_cache", "options_metrics_cache",
            "transcripts_cache",
        ):
            conn.execute(f"DELETE FROM {tbl}")
        conn.commit()
    finally:
        conn.close()
    yield


# -----------------------------------------------------------------------------
# Helpers for mocking
# -----------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload: Any = None, status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text else (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


SAMPLE_TICKER_LOOKUP = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}

SAMPLE_SUBMISSIONS = {
    "cik": "0000320193",
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "form": ["4", "4", "10-K", "4"],
            "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002", "0000000000-26-000003", "0000000000-26-000004"],
            "filingDate": ["2026-05-10", "2026-05-08", "2026-04-30", "2026-04-25"],
            "primaryDocument": ["doc1.xml", "doc2.xml", "doc3.htm", "doc4.xml"],
        }
    }
}

FORM4_XML_TEMPLATE = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerName>{name}</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>{is_director}</isDirector>
      <isOfficer>{is_officer}</isOfficer>
      <isTenPercentOwner>0</isTenPercentOwner>
      <officerTitle>{title}</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>{date}</value></transactionDate>
      <transactionCoding>
        <transactionCode>{code}</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>{shares}</value></transactionShares>
        <transactionPricePerShare><value>{price}</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>{ad}</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def _form4_xml(name="Tim Cook", title="Chief Executive Officer",
               is_officer="1", is_director="0",
               date="2026-05-09", code="P", shares=1000, price=180.0, ad="A") -> str:
    return FORM4_XML_TEMPLATE.format(
        name=name, title=title, is_officer=is_officer, is_director=is_director,
        date=date, code=code, shares=shares, price=price, ad=ad,
    )


# =============================================================================
# 1. insider_form4
# =============================================================================

def test_insider_form4_happy_path(monkeypatch):
    """Mock SEC; ensure aggregation, persistence, and ToolResult shape."""
    from tools import insider_form4 as mod
    import db

    call_counter = {"i": 0}

    # Build 3 distinct insider buys within 10 days to trigger clustered_buying
    forms = [
        _form4_xml(name="Tim Cook", title="CEO", is_officer="1",
                   date="2026-05-09", code="P", shares=5000, price=180.0),
        _form4_xml(name="Luca Maestri", title="CFO", is_officer="1",
                   date="2026-05-08", code="P", shares=2000, price=181.0),
        _form4_xml(name="Director Jane", title="", is_officer="0", is_director="1",
                   date="2026-04-25", code="P", shares=1500, price=178.0),
    ]

    def fake_sec_get(url, timeout=15):
        call_counter["i"] += 1
        if "company_tickers.json" in url:
            return _FakeResponse(payload=SAMPLE_TICKER_LOOKUP)
        if "submissions/CIK" in url:
            return _FakeResponse(payload=SAMPLE_SUBMISSIONS)
        # Form 4 doc fetch — return one of our XMLs in order. Match by filename.
        if "doc1.xml" in url:
            return _FakeResponse(text=forms[0])
        if "doc2.xml" in url:
            return _FakeResponse(text=forms[1])
        if "doc4.xml" in url:
            return _FakeResponse(text=forms[2])
        return _FakeResponse(payload={}, status_code=404)

    monkeypatch.setattr(mod, "_sec_get", fake_sec_get)

    tool = mod.InsiderForm4Tool()
    result = tool.execute(ticker="AAPL")

    assert result.is_ok(), result.error
    d = result.data
    assert d["ticker"] == "AAPL"
    assert d["lookback_days"] == 90
    assert d["total_buys"] == 3
    assert d["total_sells"] == 0
    assert d["buy_sell_ratio"] is None  # no sells
    assert d["clustered_buying"] is True
    assert d["ceo_activity"] is not None
    assert d["ceo_activity"]["type"] == "buy"
    assert d["ceo_activity"]["shares"] == 5000
    assert d["recent_trades"]
    assert result.sources
    # All sources must point at an SEC URL
    assert any("sec.gov" in (s.url or "") for s in result.sources)

    # Verify side-effect persistence to insider_trades_cache
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM insider_trades_cache WHERE ticker = 'AAPL'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) >= 3


def test_insider_form4_degraded_when_sec_fails(monkeypatch):
    """SEC unreachable -> confidence=low, no crash."""
    from tools import insider_form4 as mod

    monkeypatch.setattr(mod, "_sec_get", lambda url, timeout=15: None)

    result = mod.InsiderForm4Tool().execute(ticker="AAPL")
    assert not result.is_ok()
    assert result.confidence == "low"
    assert result.error  # graceful error string


# =============================================================================
# 2. institutional_13f
# =============================================================================

class _FakeYFTicker:
    """Mocks yfinance.Ticker for the institutional tool."""
    def __init__(self, institutional=None, mutualfund=None, major=None,
                 options=None, chain_map=None, fast_info=None, history_df=None):
        self.institutional_holders = institutional
        self.mutualfund_holders = mutualfund
        self.major_holders = major
        self.options = options or []
        self._chain_map = chain_map or {}
        self.fast_info = fast_info or {}
        self._history_df = history_df

    def option_chain(self, exp):
        return self._chain_map.get(exp)

    def history(self, period="1d"):
        return self._history_df


def _make_institutional_df():
    import pandas as pd
    return pd.DataFrame([
        {"Holder": "Vanguard Group Inc",      "Shares": 100_000_000, "Date Reported": "2026-03-31", "% Out": 8.5, "Value": 18_000_000_000},
        {"Holder": "BlackRock Inc",            "Shares": 90_000_000,  "Date Reported": "2026-03-31", "% Out": 7.5, "Value": 16_000_000_000},
        {"Holder": "Berkshire Hathaway",       "Shares": 50_000_000,  "Date Reported": "2026-03-31", "% Out": 4.0, "Value": 9_000_000_000},
        {"Holder": "State Street Corp",        "Shares": 40_000_000,  "Date Reported": "2026-03-31", "% Out": 3.3, "Value": 7_200_000_000},
        {"Holder": "FMR LLC",                  "Shares": 30_000_000,  "Date Reported": "2026-03-31", "% Out": 2.5, "Value": 5_400_000_000},
    ])


def _make_mutualfund_df():
    import pandas as pd
    return pd.DataFrame([
        {"Holder": "Vanguard Total Stock Mkt", "Shares": 20_000_000, "Date Reported": "2026-03-31", "% Out": 1.7, "Value": 3_600_000_000},
    ])


def _make_major_df():
    import pandas as pd
    # yfinance major_holders historically has unnamed cols; emulate label-style
    return pd.DataFrame([
        {0: "62.5%", 1: "% of Shares Held by Institutions"},
    ])


def test_institutional_13f_happy_path(monkeypatch):
    from tools import institutional_13f as mod
    import db

    fake = _FakeYFTicker(
        institutional=_make_institutional_df(),
        mutualfund=_make_mutualfund_df(),
        major=_make_major_df(),
    )

    class _YF:
        @staticmethod
        def Ticker(t):
            return fake

    monkeypatch.setattr("yfinance.Ticker", _YF.Ticker)

    result = mod.Institutional13FTool().execute(ticker="AAPL")
    assert result.is_ok(), result.error
    d = result.data
    assert d["ticker"] == "AAPL"
    assert d["count_holders"] >= 5
    # Top holder by value should be Vanguard
    assert d["top_holders"][0]["name"].startswith("Vanguard")
    assert d["top_holders"][0]["value_usd"] >= 1.0e10
    # is_new flag present on each
    assert all("is_new" in h for h in d["top_holders"])
    assert d["total_institutional_pct"] in (62.5,)  # parsed from major_holders
    # Persistence
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM institutional_holdings_cache WHERE ticker = 'AAPL'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) >= 5


def test_institutional_13f_degraded_when_empty(monkeypatch):
    """No holders returned -> confidence=low, no crash, ToolResult returned."""
    from tools import institutional_13f as mod

    fake = _FakeYFTicker(institutional=None, mutualfund=None, major=None)

    class _YF:
        @staticmethod
        def Ticker(t):
            return fake

    monkeypatch.setattr("yfinance.Ticker", _YF.Ticker)
    result = mod.Institutional13FTool().execute(ticker="ZZZZ")
    # Tool returns ToolResult; even with empty data is_ok() may still be True
    # since data dict isn't empty. Assert confidence degraded.
    assert result.confidence == "low"
    assert result.data["count_holders"] == 0


# =============================================================================
# 3. options_flow
# =============================================================================

def _make_calls_puts_df():
    import pandas as pd
    calls = pd.DataFrame([
        {"contractSymbol": "AAPL260619C00170000", "strike": 170.0, "lastPrice": 12.0,
         "bid": 11.9, "ask": 12.1, "volume": 500, "openInterest": 200,
         "impliedVolatility": 0.28},
        {"contractSymbol": "AAPL260619C00180000", "strike": 180.0, "lastPrice": 6.0,
         "bid": 5.9, "ask": 6.1, "volume": 4000, "openInterest": 1000,
         "impliedVolatility": 0.30},
        {"contractSymbol": "AAPL260619C00200000", "strike": 200.0, "lastPrice": 1.0,
         "bid": 0.9, "ask": 1.1, "volume": 1500, "openInterest": 500,
         "impliedVolatility": 0.33},
    ])
    puts = pd.DataFrame([
        {"contractSymbol": "AAPL260619P00160000", "strike": 160.0, "lastPrice": 1.5,
         "bid": 1.4, "ask": 1.6, "volume": 800, "openInterest": 300,
         "impliedVolatility": 0.34},
        {"contractSymbol": "AAPL260619P00180000", "strike": 180.0, "lastPrice": 5.0,
         "bid": 4.9, "ask": 5.1, "volume": 1200, "openInterest": 900,
         "impliedVolatility": 0.31},
    ])
    return calls, puts


class _FakeChain:
    def __init__(self, calls, puts):
        self.calls = calls
        self.puts = puts


def test_options_flow_happy_path(monkeypatch):
    from tools import options_flow as mod
    import db

    calls, puts = _make_calls_puts_df()
    chain = _FakeChain(calls, puts)
    fake = _FakeYFTicker(
        options=["2026-06-19"],
        chain_map={"2026-06-19": chain},
        fast_info={"last_price": 180.0, "regularMarketPrice": 180.0},
    )

    class _YF:
        @staticmethod
        def Ticker(t):
            return fake

    monkeypatch.setattr("yfinance.Ticker", _YF.Ticker)

    result = mod.OptionsFlowTool().execute(ticker="AAPL")
    assert result.is_ok(), result.error
    d = result.data
    assert d["ticker"] == "AAPL"
    assert d["underlying_price"] == 180.0
    assert d["expirations_used"] == ["2026-06-19"]
    assert d["atm_iv"] is not None and d["atm_iv"] > 0
    assert d["put_call_ratio_oi"] is not None
    assert d["put_call_ratio_volume"] is not None
    # The 180-strike call has vol/OI = 4 (>2), should appear in unusual
    assert any(u["strike"] == 180.0 and u["type"] == "call" for u in d["unusual_contracts"])
    # Sources mention yfinance options page
    assert any("options" in (s.url or "") for s in result.sources)
    # Snapshot persisted
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM options_metrics_cache WHERE ticker = 'AAPL'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["put_call_ratio"] is not None


def test_options_flow_degraded_when_no_expirations(monkeypatch):
    from tools import options_flow as mod

    fake = _FakeYFTicker(options=[])

    class _YF:
        @staticmethod
        def Ticker(t):
            return fake

    monkeypatch.setattr("yfinance.Ticker", _YF.Ticker)
    result = mod.OptionsFlowTool().execute(ticker="ZZZZ")
    assert not result.is_ok()
    assert result.confidence == "low"


# =============================================================================
# 4. transcripts
# =============================================================================

def test_transcripts_no_fmp_key(monkeypatch):
    """No FMP_API_KEY -> graceful degraded ToolResult with the documented warning."""
    from tools import transcripts as mod

    monkeypatch.delenv("FMP_API_KEY", raising=False)
    result = mod.TranscriptsTool().execute(ticker="AAPL")

    assert result.confidence == "low"
    d = result.data
    assert d["available"] is False
    assert d["transcripts"] == {}
    assert any("FMP_API_KEY" in w for w in d["warnings"])


def test_transcripts_happy_path(monkeypatch):
    from tools import transcripts as mod
    import db

    monkeypatch.setenv("FMP_API_KEY", "TEST_KEY_123")

    def fake_get(url, timeout=15):
        # Return varying content for different quarters so we can assert truncation.
        long_text = "Operator: Welcome to the call... " * 1500  # ~45k chars
        return _FakeResponse(payload=[{"content": long_text}])

    monkeypatch.setattr(mod.requests, "get", fake_get)

    result = mod.TranscriptsTool().execute(ticker="AAPL", quarters=2)
    assert result.is_ok(), result.error
    d = result.data
    assert d["available"] is True
    assert len(d["quarters_fetched"]) == 2
    # Output content truncated to ~30k + suffix
    for label, body in d["transcripts"].items():
        assert "[truncated]" in body
        assert len(body) <= mod.TRANSCRIPT_TRUNC + 50
    # Full text persisted to transcripts_cache
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT quarter, length(transcript_text) AS L FROM transcripts_cache WHERE ticker = 'AAPL'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 2
    # Persisted text is the full version (not truncated)
    assert all(r["L"] > mod.TRANSCRIPT_TRUNC for r in rows)


# =============================================================================
# Registration sanity check
# =============================================================================

def test_all_four_tools_registered():
    import tools
    names = tools.tool_names()
    for n in ("insider_form4", "institutional_13f", "options_flow", "transcripts"):
        assert n in names, f"missing tool: {n}"

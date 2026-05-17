"""
Phase 1 tool tests.

Network is mocked via monkeypatch so these run offline.  Each tool has a
happy-path test and (where relevant) a degraded-path test that proves we
return a valid ToolResult rather than crashing.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pandas as pd
import pytest

import db
import tools as tools_pkg
from tools import ToolResult


# ── Test isolation ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _wipe_tool_cache():
    """Clear the generic tool cache + catalysts between tests."""
    conn = db.get_connection()
    try:
        for tbl in ("tool_result_cache", "catalysts"):
            conn.execute(f"DELETE FROM {tbl}")
        conn.commit()
    finally:
        conn.close()
    yield


# ── Helpers ─────────────────────────────────────────────────────────────

def _years(n: int = 4) -> List[pd.Timestamp]:
    return [pd.Timestamp(f"{2025 - i}-12-31") for i in range(n)]


def _income_stmt() -> pd.DataFrame:
    """Synthetic income statement: cols are years (most recent first)."""
    cols = _years(4)
    return pd.DataFrame(
        {
            cols[0]: {
                "Total Revenue":       1200.0,
                "Gross Profit":         700.0,
                "Selling General And Administration": 200.0,
                "Reconciled Depreciation":             50.0,
                "EBIT":                 300.0,
                "Net Income":           220.0,
            },
            cols[1]: {
                "Total Revenue":       1000.0,
                "Gross Profit":         600.0,
                "Selling General And Administration": 180.0,
                "Reconciled Depreciation":             45.0,
                "EBIT":                 250.0,
                "Net Income":           180.0,
            },
            cols[2]: {
                "Total Revenue":        900.0,
                "Gross Profit":         520.0,
                "Selling General And Administration": 170.0,
                "Reconciled Depreciation":             40.0,
                "EBIT":                 200.0,
                "Net Income":           150.0,
            },
            cols[3]: {
                "Total Revenue":        800.0,
                "Gross Profit":         440.0,
                "Selling General And Administration": 160.0,
                "Reconciled Depreciation":             36.0,
                "EBIT":                 160.0,
                "Net Income":           120.0,
            },
        }
    )


def _balance_sheet() -> pd.DataFrame:
    cols = _years(4)
    return pd.DataFrame(
        {
            cols[0]: {
                "Accounts Receivable":         180.0,
                "Current Assets":              700.0,
                "Net PPE":                     500.0,
                "Total Assets":               2000.0,
                "Current Liabilities":         400.0,
                "Long Term Debt":              300.0,
                "Total Liabilities Net Minority Interest": 900.0,
                "Working Capital":             300.0,
                "Retained Earnings":           600.0,
                "Share Issued":               1000.0,
            },
            cols[1]: {
                "Accounts Receivable":         150.0,
                "Current Assets":              600.0,
                "Net PPE":                     460.0,
                "Total Assets":               1800.0,
                "Current Liabilities":         380.0,
                "Long Term Debt":              320.0,
                "Total Liabilities Net Minority Interest": 880.0,
                "Working Capital":             220.0,
                "Retained Earnings":           450.0,
                "Share Issued":               1010.0,
            },
            cols[2]: {
                "Accounts Receivable":         130.0,
                "Current Assets":              540.0,
                "Net PPE":                     430.0,
                "Total Assets":               1700.0,
                "Current Liabilities":         370.0,
                "Long Term Debt":              340.0,
                "Total Liabilities Net Minority Interest": 870.0,
                "Working Capital":             170.0,
                "Retained Earnings":           320.0,
                "Share Issued":               1015.0,
            },
            cols[3]: {
                "Accounts Receivable":         120.0,
                "Current Assets":              500.0,
                "Net PPE":                     400.0,
                "Total Assets":               1600.0,
                "Current Liabilities":         360.0,
                "Long Term Debt":              360.0,
                "Total Liabilities Net Minority Interest": 860.0,
                "Working Capital":             140.0,
                "Retained Earnings":           220.0,
                "Share Issued":               1020.0,
            },
        }
    )


def _cashflow() -> pd.DataFrame:
    cols = _years(4)
    return pd.DataFrame(
        {
            cols[0]: {"Operating Cash Flow": 260.0, "Stock Based Compensation": 50.0},
            cols[1]: {"Operating Cash Flow": 210.0, "Stock Based Compensation": 40.0},
            cols[2]: {"Operating Cash Flow": 170.0, "Stock Based Compensation": 35.0},
            cols[3]: {"Operating Cash Flow": 140.0, "Stock Based Compensation": 30.0},
        }
    )


class _FakeTicker:
    def __init__(self, income=None, balance=None, cashflow=None, info=None,
                 calendar=None, history_df=None):
        self.income_stmt = income if income is not None else _income_stmt()
        self.balance_sheet = balance if balance is not None else _balance_sheet()
        self.cashflow = cashflow if cashflow is not None else _cashflow()
        self.info = info if info is not None else {"marketCap": 5_000.0, "longName": "Fake Co"}
        self.calendar = calendar
        self._history_df = history_df

    def history(self, period: str = "1y"):
        return self._history_df


# ============================================================================
# QoE Forensics
# ============================================================================

def test_qoe_forensics_happy_path(monkeypatch):
    fake_yf = SimpleNamespace(Ticker=lambda t: _FakeTicker())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.qoe_forensics import QoEForensicsTool
    result = QoEForensicsTool().execute(ticker="NVDA")

    assert isinstance(result, ToolResult)
    assert result.is_ok(), f"expected ok, got error={result.error}"
    d = result.data
    assert "beneish_m_score" in d
    assert d["beneish_m_score"] is not None
    assert d["altman_z_score"] is not None
    assert d["piotroski_f_score"] is not None
    assert 0 <= d["piotroski_f_score"] <= 9
    assert d["accrual_ratio"] is not None
    assert d["sbc_pct_revenue"] is not None
    assert d["year_analyzed"]
    assert isinstance(d["warnings"], list)
    assert result.confidence in ("medium", "high")
    # Should have one source per computed metric
    fields = {s.field for s in result.sources}
    for need in ("beneish_m_score", "altman_z_score", "piotroski_f_score"):
        assert need in fields


def test_qoe_forensics_degraded_when_no_financials(monkeypatch):
    """If yfinance returns empty frames, the tool still returns a ToolResult."""
    empty = pd.DataFrame()
    fake = _FakeTicker(income=empty, balance=empty, cashflow=empty, info={})
    fake_yf = SimpleNamespace(Ticker=lambda t: fake)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.qoe_forensics import QoEForensicsTool
    result = QoEForensicsTool().execute(ticker="ZZZZ")
    assert isinstance(result, ToolResult)
    assert result.error is None  # should NOT crash
    assert result.confidence == "low"
    assert result.data.get("warnings")
    # No core metric should be computable
    assert result.data.get("beneish_m_score") is None
    assert result.data.get("altman_z_score") is None


# ============================================================================
# Macro Context
# ============================================================================

def _make_history(prices: List[float]) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-17", periods=len(prices), freq="B")
    return pd.DataFrame({"Close": prices}, index=idx)


def test_macro_context_happy_path(monkeypatch):
    # Manufacture a healthy market: VIX=14, curve +1.5%, HYG positive
    histories = {
        "^TNX":    _make_history([4.0] * 250 + [4.5]),
        "^TYX":    _make_history([4.2] * 250 + [4.7]),
        "^IRX":    _make_history([3.0] * 250 + [3.0]),
        "^VIX":    _make_history([14.0] * 250 + [14.0]),
        "^VIX9D":  _make_history([13.5] * 250 + [13.5]),
        "DX-Y.NYB":_make_history([100.0] * 250 + [101.0]),
        # HYG: flat then rising — last is higher than t-30
        "HYG":     _make_history([80.0] * 220 + list(80.0 + 0.1 * i for i in range(31))),
        "LQD":     _make_history([100.0] * 220 + list(100.0 + 0.02 * i for i in range(31))),
        "^GSPC":   _make_history([4500.0] * 200 + [5000.0] * 51),
    }

    class FakeYFTicker:
        def __init__(self, t):
            self._t = t

        def history(self, period="1y"):
            return histories.get(self._t)

    fake_yf = SimpleNamespace(Ticker=FakeYFTicker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.macro_context import MacroContextTool
    result = MacroContextTool().execute()
    assert isinstance(result, ToolResult)
    assert result.is_ok()
    d = result.data
    assert d["yield_10y"] == pytest.approx(4.5)
    assert d["yield_2y_proxy"] == pytest.approx(3.0)
    assert d["yield_curve_slope_bps"] == pytest.approx(150.0)
    assert d["yield_curve_inverted"] is False
    assert d["vix"] == pytest.approx(14.0)
    assert d["vix_regime"] == "low"
    assert d["regime"] == "risk_on"
    assert "regime_summary" in d
    assert d["snapshot_date"]
    # Sources should cite yfinance per-variable
    assert any(s.field == "yield_10y" for s in result.sources)
    assert any(s.field == "vix" for s in result.sources)


def test_macro_context_degraded_when_data_missing(monkeypatch):
    """If everything fails, tool should return low confidence with warnings."""
    class BlankTicker:
        def __init__(self, t):
            pass
        def history(self, period="1y"):
            return pd.DataFrame()  # empty

    fake_yf = SimpleNamespace(Ticker=BlankTicker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.macro_context import MacroContextTool
    result = MacroContextTool().execute()
    assert isinstance(result, ToolResult)
    assert result.error is None
    assert result.confidence == "low"
    assert result.data["warnings"]
    assert result.data["vix"] is None


# ============================================================================
# Catalyst Lookup
# ============================================================================

def test_catalyst_lookup_happy_path(monkeypatch):
    fake_cal = {
        "Earnings Date": [pd.Timestamp("2026-08-20")],
        "Ex-Dividend Date": pd.Timestamp("2026-07-15"),
    }
    fake_ticker = _FakeTicker(calendar=fake_cal)
    fake_yf = SimpleNamespace(Ticker=lambda t: fake_ticker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.catalyst_lookup import CatalystLookupTool
    result = CatalystLookupTool().execute(ticker="NVDA")
    assert isinstance(result, ToolResult)
    assert result.is_ok()
    d = result.data
    assert d["ticker"] == "NVDA"
    assert d["earnings_date"] == "2026-08-20"
    assert d["dividend_date"] == "2026-07-15"
    # Company-specific list should include earnings + dividend
    types = {ev["type"] for ev in d["company_specific"]}
    assert "earnings" in types and "dividend" in types
    # Market-wide should have at least one FOMC/CPI/NFP entry
    assert d["market_wide"]
    # Should have persisted in catalysts table
    persisted = db.get_catalysts(tickers=["NVDA"], days_ahead=365 * 2)
    persisted_types = {ev["event_type"] for ev in persisted}
    assert "earnings" in persisted_types


def test_catalyst_lookup_handles_missing_calendar(monkeypatch):
    """If yfinance .calendar raises, the tool still returns market-wide events."""
    class BrokenTicker:
        @property
        def calendar(self):
            raise RuntimeError("calendar broken")

    fake_yf = SimpleNamespace(Ticker=lambda t: BrokenTicker())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    from tools.catalyst_lookup import CatalystLookupTool
    result = CatalystLookupTool().execute(ticker="ZZZZ")
    assert isinstance(result, ToolResult)
    assert result.error is None
    assert result.data["earnings_date"] is None
    assert result.data["warnings"]
    # market_wide static calendar should still produce entries
    assert isinstance(result.data["market_wide"], list)


# ============================================================================
# Alt Data
# ============================================================================

def test_alt_data_degraded_without_pytrends(monkeypatch):
    """Most common case: pytrends not installed → low confidence, no crash."""
    # Force the optional import to fail
    monkeypatch.setitem(sys.modules, "pytrends", None)  # any import will ImportError
    from tools import alt_data as alt_mod
    monkeypatch.setattr(alt_mod, "_check_optional_import", lambda: (False, None))

    result = alt_mod.AltDataTool().execute(ticker="NVDA")
    assert isinstance(result, ToolResult)
    assert result.error is None
    assert result.confidence == "low"
    assert result.data["available"] is False
    assert result.data["google_trends_score"] is None
    assert "pytrends not installed" in result.data["warnings"]


def test_alt_data_happy_path_with_mock_pytrends(monkeypatch):
    """Simulate pytrends being available and returning a trend frame."""
    # Build a fake interest_over_time DataFrame: 12 weekly rows
    idx = pd.date_range(end="2026-05-17", periods=12, freq="W")
    df = pd.DataFrame({"NVDA": [40, 45, 50, 55, 60, 65, 70, 75, 78, 80, 82, 85],
                       "isPartial": [False] * 12}, index=idx)

    class FakeTrendReq:
        def __init__(self, **kw):
            pass
        def build_payload(self, *a, **kw):
            pass
        def interest_over_time(self):
            return df

    from tools import alt_data as alt_mod
    monkeypatch.setattr(alt_mod, "_check_optional_import", lambda: (True, FakeTrendReq))

    # yfinance for company name lookup
    fake_yf = SimpleNamespace(Ticker=lambda t: _FakeTicker())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    result = alt_mod.AltDataTool().execute(ticker="NVDA")
    assert isinstance(result, ToolResult)
    assert result.is_ok()
    d = result.data
    assert d["available"] is True
    assert d["google_trends_score"] == 85
    assert d["google_trends_30d_delta"] is not None
    assert d["trend_direction"] in ("rising", "falling", "stable")
    assert result.confidence == "medium"
    assert any(s.field == "google_trends_score" for s in result.sources)

"""
Tests for screener_engine — rule-walking over cached tool data.

The fundamentals/technicals/financial_trends tools are mocked at the registry
level so no network is hit.
"""
from __future__ import annotations

import pytest

import db
import screener_engine as se
from tools import ToolResult


# ── Fake tool data keyed by ticker ────────────────────────────────────────

FAKE = {
    "NVDA": {
        "fundamentals": {"current_price": 200.0, "forward_pe": 40.0, "revenue_growth": 0.25, "market_cap": 5e12},
        "technicals": {"rsi": 25.0, "golden_cross": True, "year_return_pct": 80.0, "relative_strength_vs_spy": 1.5},
        "trends": {"quarter_count": 8, "trend_signals": {"yoy_revenue_growth": 0.25}},
    },
    "AMD": {
        "fundamentals": {"current_price": 100.0, "forward_pe": 30.0, "revenue_growth": 0.10, "market_cap": 2e11},
        "technicals": {"rsi": 55.0, "golden_cross": False, "year_return_pct": 10.0, "relative_strength_vs_spy": 0.9},
        "trends": {"quarter_count": 8, "trend_signals": {"yoy_revenue_growth": 0.10}},
    },
    "INTC": {
        "fundamentals": {"current_price": 40.0, "forward_pe": 15.0, "revenue_growth": -0.05, "market_cap": 1.5e11},
        "technicals": {"rsi": 28.0, "golden_cross": False, "year_return_pct": -20.0, "relative_strength_vs_spy": 0.6},
        "trends": {"quarter_count": 8, "trend_signals": {"yoy_revenue_growth": -0.05}},
    },
}


@pytest.fixture(autouse=True)
def _mock_tools(monkeypatch):
    def fake_gather(ticker, snapshot_row=None, fetch_technical=True):
        d = FAKE.get(ticker.upper(), {})
        return {
            "fundamentals": d.get("fundamentals", {}),
            "technicals": d.get("technicals", {}) if fetch_technical else {},
            "trends": d.get("trends", {}) if fetch_technical else {},
        }
    monkeypatch.setattr(se, "_gather_ticker_data", fake_gather)
    yield


def test_single_rule_rsi_lt_30():
    spec = {"universe": ["NVDA", "AMD", "INTC"], "rules": [{"field": "rsi", "op": "<", "value": 30}], "combine": "AND"}
    out = se.run_screen(spec)
    matched = {m["ticker"] for m in out["matches"]}
    assert matched == {"NVDA", "INTC"}  # rsi 25 and 28
    assert out["evaluated"] == 3


def test_and_combine_multiple_rules():
    spec = {
        "universe": ["NVDA", "AMD", "INTC"],
        "rules": [
            {"field": "rsi", "op": "<", "value": 30},
            {"field": "yoy_revenue_growth", "op": ">", "value": 0.20},
        ],
        "combine": "AND",
    }
    out = se.run_screen(spec)
    matched = {m["ticker"] for m in out["matches"]}
    assert matched == {"NVDA"}  # only NVDA has rsi<30 AND growth>20%


def test_or_combine():
    spec = {
        "universe": ["NVDA", "AMD", "INTC"],
        "rules": [
            {"field": "ma_50_above_ma_200", "op": "=", "value": True},
            {"field": "year_return_pct", "op": ">", "value": 50},
        ],
        "combine": "OR",
    }
    out = se.run_screen(spec)
    matched = {m["ticker"] for m in out["matches"]}
    assert matched == {"NVDA"}  # golden_cross True OR year_return>50 (both NVDA)


def test_boolean_field_match():
    spec = {"universe": ["NVDA", "AMD"], "rules": [{"field": "ma_50_above_ma_200", "op": "=", "value": True}], "combine": "AND"}
    out = se.run_screen(spec)
    assert {m["ticker"] for m in out["matches"]} == {"NVDA"}


def test_match_includes_field_values():
    spec = {"universe": ["NVDA"], "rules": [{"field": "rsi", "op": "<", "value": 30}], "combine": "AND"}
    out = se.run_screen(spec)
    assert out["matches"][0]["values"]["rsi"] == 25.0


def test_empty_universe_errors():
    out = se.run_screen({"universe": [], "rules": [{"field": "rsi", "op": "<", "value": 30}]})
    assert out["error"] == "empty universe"


def test_no_rules_errors():
    out = se.run_screen({"universe": ["NVDA"], "rules": []})
    assert out["error"] == "no rules"


def test_unknown_field_does_not_pass_and():
    spec = {"universe": ["NVDA"], "rules": [{"field": "not_a_field", "op": ">", "value": 1}], "combine": "AND"}
    out = se.run_screen(spec)
    # No evaluable rule → ticker dropped
    assert out["matches"] == []


def test_resolve_universe_watchlist(monkeypatch):
    monkeypatch.setattr(db, "get_watchlist", lambda: [{"ticker": "NVDA"}, {"ticker": "MU"}])
    assert se.resolve_universe("watchlist") == ["NVDA", "MU"]


def test_available_fields_includes_core():
    fields = se.available_fields()
    for need in ("rsi", "forward_pe", "yoy_revenue_growth", "ma_50_above_ma_200", "pattern",
                 "pct_from_52w_high", "year_change_pct"):
        assert need in fields


# ── S&P 500 universe (snapshot fast path) ─────────────────────────────────

# pct_from_high and year_change are fractions in the real snapshot (-0.01 = -1%).
_SNAPSHOT = {
    "AAA": {"ticker": "AAA", "current_price": 100, "market_cap": 5e10, "forward_pe": 18,
            "revenue_growth": 0.2, "pct_from_high": -0.01, "year_change": 0.60, "day_change_percent": 1.2},
    "BBB": {"ticker": "BBB", "current_price": 50, "market_cap": 2e9, "forward_pe": 9,
            "revenue_growth": 0.05, "pct_from_high": -0.40, "year_change": -0.15, "day_change_percent": -2.0},
}


def test_sp500_snapshot_fast_path(monkeypatch):
    # Real gather is restored (autouse mock replaced it) by patching it to use snapshot rows.
    def gather(ticker, snapshot_row=None, fetch_technical=True):
        return {"fundamentals": se._snapshot_to_fundamentals(snapshot_row) if snapshot_row else {},
                "technicals": {}, "trends": {}}
    monkeypatch.setattr(se, "_gather_ticker_data", gather)
    monkeypatch.setattr(se, "resolve_universe", lambda spec: ["AAA", "BBB"])
    monkeypatch.setattr("tools.sp500_lookup.sp500_snapshot", lambda: _SNAPSHOT)

    spec = {"universe": "sp500", "combine": "AND",
            "rules": [{"field": "pct_from_52w_high", "op": ">=", "value": -2}]}
    out = se.run_screen(spec)
    assert {m["ticker"] for m in out["matches"]} == {"AAA"}  # only AAA is near its high


def test_sp500_technical_rule_needs_scan(monkeypatch):
    monkeypatch.setattr(se, "resolve_universe", lambda spec: ["AAA", "BBB"])
    monkeypatch.setattr("tools.sp500_lookup.sp500_snapshot", lambda: _SNAPSHOT)
    spec = {"universe": "sp500", "combine": "AND",
            "rules": [{"field": "rsi", "op": "<", "value": 30}]}
    out = se.run_screen(spec)
    assert out.get("needs_scan") is True
    assert out["error"] == "needs_scan"


def test_sp500_technical_rule_runs_with_scan(monkeypatch):
    def gather(ticker, snapshot_row=None, fetch_technical=True):
        return {"fundamentals": {}, "technicals": {"rsi": 20.0} if fetch_technical else {}, "trends": {}}
    monkeypatch.setattr(se, "_gather_ticker_data", gather)
    monkeypatch.setattr(se, "resolve_universe", lambda spec: ["AAA"])
    monkeypatch.setattr("tools.sp500_lookup.sp500_snapshot", lambda: _SNAPSHOT)
    spec = {"universe": "sp500", "combine": "AND", "scan": True,
            "rules": [{"field": "rsi", "op": "<", "value": 30}]}
    out = se.run_screen(spec)
    assert {m["ticker"] for m in out["matches"]} == {"AAA"}


def test_pattern_rule_matches(monkeypatch):
    monkeypatch.setattr(se, "resolve_universe", lambda spec: ["NVDA", "AMD"])
    monkeypatch.setattr(se, "_detect_patterns",
                        lambda t: {"cup_and_handle"} if t == "NVDA" else set())
    spec = {"universe": ["NVDA", "AMD"], "combine": "AND",
            "rules": [{"field": "pattern", "op": "is", "value": "cup_and_handle"}]}
    out = se.run_screen(spec)
    assert {m["ticker"] for m in out["matches"]} == {"NVDA"}
    assert out["matches"][0]["values"]["pattern"] == ["cup_and_handle"]


def test_partial_match_flags_missing_field(monkeypatch):
    spec = {"universe": ["NVDA"], "combine": "AND", "rules": [
        {"field": "rsi", "op": "<", "value": 30},
        {"field": "not_a_field", "op": ">", "value": 1},
    ]}
    out = se.run_screen(spec)
    assert out["matches"][0]["partial"] is True
    assert "not_a_field" in out["matches"][0]["missing_fields"]


def test_pattern_names_exposed():
    names = se.pattern_names()
    assert "head_shoulders" in names and "cup_and_handle" in names


# ── Endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture
def client():
    import app as _app
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


def test_screener_run_endpoint(client, monkeypatch):
    monkeypatch.setattr(se, "resolve_universe", lambda spec: ["NVDA", "AMD"])
    res = client.post("/api/screener/run", json={
        "universe": ["NVDA", "AMD"],
        "rules": [{"field": "rsi", "op": "<", "value": 30}],
        "combine": "AND",
    })
    assert res.status_code == 200
    body = res.get_json()
    assert {m["ticker"] for m in body["matches"]} == {"NVDA"}


def test_screener_fields_endpoint(client):
    res = client.get("/api/screener/fields")
    assert res.status_code == 200
    assert "rsi" in res.get_json()["fields"]


def test_screener_saved_crud(client):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM screener_saved")
        conn.commit()
    finally:
        conn.close()

    spec = {"universe": "themes", "combine": "AND", "rules": [{"field": "rsi", "op": "<", "value": 30}]}
    created = client.post("/api/screener/saved", json={"name": "Oversold growth", "rules": spec})
    assert created.status_code == 200
    sid = created.get_json()["id"]

    listed = client.get("/api/screener/saved").get_json()["saved"]
    assert any(s["id"] == sid and s["name"] == "Oversold growth" for s in listed)
    assert listed[0]["rules"]["combine"] == "AND"

    assert client.delete(f"/api/screener/saved/{sid}").status_code == 200
    listed2 = client.get("/api/screener/saved").get_json()["saved"]
    assert not any(s["id"] == sid for s in listed2)


def test_screener_saved_requires_name(client):
    res = client.post("/api/screener/saved", json={"rules": {}})
    assert res.status_code == 400

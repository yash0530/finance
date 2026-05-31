from __future__ import annotations

import pytest

import app as _app
import db
import portfolio_manual_service as svc


@pytest.fixture(autouse=True)
def _wipe_portfolio_tables():
    conn = db.get_connection()
    try:
        for table in ("portfolio_holdings", "theme_tickers", "themes"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture
def client():
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


def test_manual_holding_crud_roundtrip():
    holding = svc.create_holding({"ticker": "nvda", "shares": 2, "avg_cost": 100})
    assert holding["id"] > 0
    assert holding["ticker"] == "NVDA"
    assert holding["source"] == "manual"

    updated = svc.update_holding(holding["id"], {"shares": 3, "avg_cost": 110})
    assert updated["shares"] == 3
    assert updated["avg_cost"] == 110

    rows = svc.list_holdings()
    assert [r["ticker"] for r in rows] == ["NVDA"]

    assert svc.delete_holding(holding["id"]) is True
    assert svc.list_holdings() == []


def test_manual_holding_validation():
    with pytest.raises(svc.PortfolioValidationError):
        svc.create_holding({"ticker": "bad symbol", "shares": 1})
    with pytest.raises(svc.PortfolioValidationError):
        svc.create_holding({"ticker": "NVDA", "shares": 0})
    with pytest.raises(svc.PortfolioValidationError):
        svc.create_holding({"ticker": "NVDA", "shares": 1, "avg_cost": -1})


def test_summary_aggregates_quotes_and_theme_exposure(monkeypatch):
    db.upsert_theme("ai", "AI Infra")
    db.add_theme_ticker("ai", "NVDA")
    svc.create_holding({"ticker": "NVDA", "shares": 2, "avg_cost": 100})
    svc.create_holding({"ticker": "NVDA", "shares": 1, "avg_cost": 120})
    svc.create_holding({"ticker": "CASH", "shares": 100, "avg_cost": 1})

    monkeypatch.setattr(
        svc,
        "_fetch_quotes",
        lambda tickers: {
            "NVDA": {"price": 150, "change_pct": 2.5},
            "CASH": {"price": 1, "change_pct": 0},
        },
    )

    summary = svc.summary(include_quotes=True)
    assert summary["count"] == 3
    assert summary["position_count"] == 2
    assert summary["total_cost_basis"] == pytest.approx(420)
    assert summary["total_position_value"] == pytest.approx(550)
    assert summary["known_unrealized_gain"] == pytest.approx(130)

    by_ticker = {p["ticker"]: p for p in summary["positions"]}
    assert by_ticker["NVDA"]["shares"] == 3
    assert by_ticker["NVDA"]["avg_cost"] == pytest.approx(106.6666667)
    assert by_ticker["NVDA"]["weight_pct"] == pytest.approx(81.8181818)
    assert summary["theme_exposure"]["AI Infra"] == pytest.approx(450)
    assert summary["theme_exposure"]["Unmapped"] == pytest.approx(100)
    assert summary["source_exposure"]["manual"] == pytest.approx(550)


def test_csv_import_can_replace_manual_without_touching_other_sources():
    svc.create_holding({"ticker": "OLD", "shares": 1, "avg_cost": 10})
    conn = db.get_connection()
    try:
        conn.execute(
            """INSERT INTO portfolio_holdings (ticker, shares, avg_cost, source, synced_at)
               VALUES ('KEEP', 1, 20, 'robinhood', datetime('now'))"""
        )
        conn.commit()
    finally:
        conn.close()

    result = svc.import_csv("ticker,shares,avg_cost\nNVDA,2,100\nAMD,3,80", replace_manual=True)
    assert result == {"ok": True, "imported": 2, "errors": []}

    rows = svc.list_holdings()
    assert {r["ticker"] for r in rows} == {"AMD", "KEEP", "NVDA"}
    by_ticker = {r["ticker"]: r for r in rows}
    assert by_ticker["KEEP"]["source"] == "robinhood"
    assert by_ticker["NVDA"]["source"] == "manual_csv"


def test_csv_import_reports_line_errors():
    result = svc.import_csv("ticker,shares,avg_cost\nNVDA,0,100\nbad symbol,1,2")
    assert result["ok"] is False
    assert result["imported"] == 0
    assert [e["line"] for e in result["errors"]] == [2, 3]


def test_portfolio_endpoints_crud_and_summary(client, monkeypatch):
    monkeypatch.setattr(
        svc,
        "_fetch_quotes",
        lambda tickers: {"NVDA": {"price": 125, "change_pct": 1.0}},
    )

    created = client.post("/api/portfolio/holdings", json={
        "ticker": "nvda",
        "shares": 2,
        "avg_cost": 100,
    })
    assert created.status_code == 200
    holding_id = created.get_json()["holding"]["id"]

    listed = client.get("/api/portfolio/holdings").get_json()
    assert listed["holdings"][0]["ticker"] == "NVDA"

    summary = client.get("/api/portfolio/summary").get_json()
    assert summary["positions"][0]["current_value"] == pytest.approx(250)

    updated = client.put(f"/api/portfolio/holdings/{holding_id}", json={"shares": 3})
    assert updated.status_code == 200
    assert updated.get_json()["holding"]["shares"] == 3

    deleted = client.delete(f"/api/portfolio/holdings/{holding_id}")
    assert deleted.status_code == 200
    assert client.get("/api/portfolio/holdings").get_json()["holdings"] == []


def test_portfolio_endpoint_validation(client):
    res = client.post("/api/portfolio/holdings", json={"ticker": "", "shares": 1})
    assert res.status_code == 400
    assert "ticker" in res.get_json()["error"]

    res = client.put("/api/portfolio/holdings/999", json={"ticker": "NVDA", "shares": 1})
    assert res.status_code == 404

    res = client.post("/api/portfolio/import", json={"csv": "ticker,shares\nNVDA,0"})
    assert res.status_code == 400
    assert res.get_json()["ok"] is False

from __future__ import annotations

import db
import pattern_service
import pytest

import app as _app


@pytest.fixture
def client():
    _app.app.config["TESTING"] = True
    with _app.app.test_client() as c:
        yield c


def _wipe_cache():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache WHERE tool_name LIKE 'pattern_scan%'")
        conn.commit()
    finally:
        conn.close()


def test_pattern_catalog_includes_restored_triples():
    keys = {p["key"] for p in pattern_service.pattern_catalog()}
    assert "triple_top" in keys
    assert "triple_bottom" in keys


def test_scan_ticker_normalizes_and_enriches_pattern(monkeypatch):
    _wipe_cache()

    def fake_detector(prices, dates):
        return {
            "detected": True,
            "confidence": 88,
            "target_price": 42.4242,
        }

    monkeypatch.setattr(pattern_service, "_pattern_catalog_map", lambda: {
        "double_bottom": {
            "key": "double_bottom",
            "name": "Double Bottom",
            "signal": "bullish",
            "detector": fake_detector,
        }
    })
    monkeypatch.setattr(pattern_service, "_company_lookup", lambda: {
        "TEST": {"company_name": "Test Co", "sector": "Technology"}
    })
    monkeypatch.setattr(pattern_service, "_bars_for_ticker", lambda ticker: [
        {"time": f"2026-01-{(i % 28) + 1:02d}", "close": float(i + 10)}
        for i in range(35)
    ])

    result = pattern_service.scan_ticker("test", "double-bottom", refresh=True)

    assert result["detected"] is True
    assert result["pattern_type"] == "double_bottom"
    assert result["pattern_name"] == "Double Bottom"
    assert result["signal"] == "bullish"
    assert result["company_name"] == "Test Co"
    assert result["target_price"] == 42.42


def test_pattern_endpoints(client, monkeypatch):
    monkeypatch.setattr(pattern_service, "scan_universe", lambda **kwargs: {
        "title": "Technical Patterns",
        "evaluated": 1,
        "pattern_types": {},
        "summary": {"total_patterns": 0, "bullish_patterns": 0, "bearish_patterns": 0},
    })
    monkeypatch.setattr(pattern_service, "scan_ticker", lambda *args, **kwargs: {
        "ticker": "TEST",
        "pattern_type": "double_bottom",
        "detected": False,
        "patterns": [],
    })

    all_res = client.get("/api/patterns/all?limit=1")
    assert all_res.status_code == 200
    assert all_res.get_json()["evaluated"] == 1

    ticker_res = client.get("/api/patterns/double-bottom/TEST")
    assert ticker_res.status_code == 200
    assert ticker_res.get_json()["pattern_type"] == "double_bottom"

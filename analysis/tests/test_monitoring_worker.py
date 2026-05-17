"""
test_monitoring_worker.py — B3 hourly thesis-decay monitor tests.

We monkeypatch the LLM (`check_thesis_decay`) and sentiment service to keep
tests offline and deterministic.
"""
from datetime import date, datetime, timedelta
from typing import Dict

import pytest

import db
import monitoring_worker as mw


@pytest.fixture(autouse=True)
def _clean_state():
    """Wipe monitoring/recommendations between tests."""
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM monitoring_digest")
        conn.execute("DELETE FROM monitoring_enabled")
        conn.execute("DELETE FROM recommendations")
        conn.execute("DELETE FROM portfolio_holdings")
        conn.commit()
    finally:
        conn.close()
    yield


def _insert_holding(ticker: str):
    db.upsert_holdings([{
        "ticker": ticker, "shares": 10.0, "avg_cost": 100.0, "source": "test",
    }])


def _insert_rec(ticker: str, wwcm: str = "Revenue growth drops below 15%") -> int:
    return db.save_recommendation(
        report_id=f"rep-{ticker.lower()}",
        ticker=ticker,
        recommendation="BUY",
        conviction="MEDIUM",
        price_at_recommendation=100.0,
        target_low=110.0,
        target_high=130.0,
        thesis_summary=f"{ticker} bull thesis",
        what_would_change_mind=wwcm,
    )


def test_no_holdings_no_recs_returns_empty(monkeypatch):
    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)
    assert mw.run_digest_once() == []


def test_holding_without_rec_is_skipped(monkeypatch):
    _insert_holding("NVDA")
    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)
    monkeypatch.setattr("llm_service.check_thesis_decay", lambda *a, **kw: {"decayed": True, "severity": "high"})

    items = mw.run_digest_once()
    # No rec on file → no LLM call → no digest item
    assert items == []


def test_decayed_signal_is_persisted(monkeypatch):
    _insert_holding("NVDA")
    _insert_rec("NVDA")

    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: {
        "score": 3.5, "label": "bearish",
        "headlines": [{"title": "Nvidia guides revenue growth down"}],
    })
    monkeypatch.setattr("llm_service.check_thesis_decay", lambda *a, **kw: {
        "decayed": True,
        "severity": "high",
        "signal_summary": "Q4 guide cut",
        "triggered_criteria": ["revenue growth drops below 15%"],
        "evidence_summary": "Nvidia guides Q4 revenue growth down to 12%",
    })

    items = mw.run_digest_once()
    assert len(items) == 1
    item = items[0]
    assert item["ticker"] == "NVDA"
    assert item["severity"] == "high"
    assert item["decayed"] is True

    # Persisted to today's digest
    digests = db.get_recent_digests(days=1)
    assert len(digests) == 1
    assert digests[0]["ticker"] == "NVDA"
    assert digests[0]["digest_date"] == date.today().isoformat()
    assert len(digests[0]["items"]) == 1


def test_non_decayed_signal_is_not_persisted(monkeypatch):
    _insert_holding("AAPL")
    _insert_rec("AAPL")

    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)
    monkeypatch.setattr("llm_service.check_thesis_decay", lambda *a, **kw: {
        "decayed": False, "severity": "low",
        "signal_summary": "no material news",
        "triggered_criteria": [], "evidence_summary": "",
    })

    items = mw.run_digest_once()
    assert items == []
    assert db.get_recent_digests(days=1) == []


def test_dedup_suppresses_equal_severity(monkeypatch):
    _insert_holding("NVDA")
    _insert_rec("NVDA")
    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)

    # First run: medium severity decay → persisted
    monkeypatch.setattr("llm_service.check_thesis_decay", lambda *a, **kw: {
        "decayed": True, "severity": "medium",
        "signal_summary": "weakening demand signals",
        "triggered_criteria": ["growth slowdown"],
        "evidence_summary": "Headline A",
    })
    first = mw.run_digest_once()
    assert len(first) == 1

    # Second run: same severity → suppressed (no new persist)
    second = mw.run_digest_once()
    assert second == []

    digests = db.get_recent_digests(days=1)
    assert len(digests[0]["items"]) == 1


def test_dedup_allows_severity_upgrade(monkeypatch):
    _insert_holding("NVDA")
    _insert_rec("NVDA")
    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)

    calls = {"n": 0}
    def fake_check(*a, **kw):
        calls["n"] += 1
        sev = "medium" if calls["n"] == 1 else "high"
        return {
            "decayed": True, "severity": sev,
            "signal_summary": "decay", "triggered_criteria": ["x"], "evidence_summary": "",
        }
    monkeypatch.setattr("llm_service.check_thesis_decay", fake_check)

    first = mw.run_digest_once()
    second = mw.run_digest_once()

    assert len(first) == 1
    assert first[0]["severity"] == "medium"
    assert len(second) == 1
    assert second[0]["severity"] == "high"

    digests = db.get_recent_digests(days=1)
    items = digests[0]["items"]
    assert len(items) == 2
    severities = [i["severity"] for i in items]
    assert severities == ["medium", "high"]


def test_stale_rec_is_skipped(monkeypatch):
    """Recommendations older than _REC_MAX_AGE_DAYS should not trigger LLM calls."""
    _insert_holding("OLD")
    rec_id = _insert_rec("OLD")

    # Hand-edit the rec's created_at to make it ancient
    old_date = (datetime.now() - timedelta(days=mw._REC_MAX_AGE_DAYS + 5)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE recommendations SET created_at = ? WHERE id = ?",
            (old_date, rec_id),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)
    called = {"n": 0}
    def fake_check(*a, **kw):
        called["n"] += 1
        return {"decayed": True, "severity": "high"}
    monkeypatch.setattr("llm_service.check_thesis_decay", fake_check)

    items = mw.run_digest_once()
    assert items == []
    assert called["n"] == 0  # never asked the LLM


def test_monitoring_enabled_overrides_holdings(monkeypatch):
    """If any ticker is opted in via monitoring_enabled, only those run."""
    _insert_holding("AAPL")
    _insert_holding("NVDA")
    _insert_rec("AAPL")
    _insert_rec("NVDA")

    db.enable_monitoring("AAPL")  # only AAPL opted in
    monkeypatch.setattr(mw, "_fetch_sentiment_snapshot", lambda t: None)

    seen = []
    def fake_check(rec, **kw):
        seen.append(rec["ticker"])
        return {"decayed": True, "severity": "high", "signal_summary": "x",
                "triggered_criteria": ["c"], "evidence_summary": ""}
    monkeypatch.setattr("llm_service.check_thesis_decay", fake_check)

    items = mw.run_digest_once()
    assert seen == ["AAPL"]
    assert [i["ticker"] for i in items] == ["AAPL"]

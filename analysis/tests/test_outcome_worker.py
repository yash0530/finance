"""
test_outcome_worker.py — B4 outcome auto-population tests.

We inject a `close_fn` to avoid hitting yfinance.
"""
from datetime import datetime, timedelta

import pytest

import db
import outcome_worker as ow


@pytest.fixture(autouse=True)
def _clean_recs():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM recommendations")
        conn.commit()
    finally:
        conn.close()
    yield


def _insert_rec_at(ticker: str, days_ago: int, price: float = 100.0, rec_text: str = "BUY",
                   conviction: str = "MEDIUM") -> int:
    rec_id = db.save_recommendation(
        report_id=f"rep-{ticker.lower()}-{days_ago}",
        ticker=ticker, recommendation=rec_text, conviction=conviction,
        price_at_recommendation=price,
        target_low=price * 1.1, target_high=price * 1.3,
        thesis_summary="t", what_would_change_mind="x",
    )
    backdated = (datetime.now() - timedelta(days=days_ago)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute("UPDATE recommendations SET created_at = ? WHERE id = ?", (backdated, rec_id))
        conn.commit()
    finally:
        conn.close()
    return rec_id


def test_no_recs_returns_empty_summary():
    summary = ow.run_backfill_once(close_fn=lambda *a: None)
    assert summary["recommendations_scanned"] == 0
    assert summary["recommendations_updated"] == 0


def test_young_rec_no_horizon_filled():
    _insert_rec_at("AAPL", days_ago=5)
    fake_close = lambda t, d: 150.0
    summary = ow.run_backfill_once(close_fn=fake_close)
    assert summary["horizons_filled"] == 0


def test_1m_horizon_filled_when_due():
    rec_id = _insert_rec_at("AAPL", days_ago=35, price=100.0)
    fake_close = lambda t, d: 110.0
    summary = ow.run_backfill_once(close_fn=fake_close)
    assert summary["recommendations_updated"] == 1
    assert summary["horizons_filled"] == 1

    refreshed = db.get_recommendations("AAPL")[0]
    assert refreshed["outcome_1m_return_pct"] == 10.0
    assert refreshed["outcome_3m_return_pct"] is None
    assert refreshed["outcome_6m_return_pct"] is None
    assert refreshed["outcome_1y_return_pct"] is None


def test_all_horizons_filled_for_year_old_rec():
    _insert_rec_at("AAPL", days_ago=380, price=100.0)
    fake_close = lambda t, d: 120.0
    summary = ow.run_backfill_once(close_fn=fake_close)
    assert summary["horizons_filled"] == 4

    r = db.get_recommendations("AAPL")[0]
    assert r["outcome_1m_return_pct"] == 20.0
    assert r["outcome_3m_return_pct"] == 20.0
    assert r["outcome_6m_return_pct"] == 20.0
    assert r["outcome_1y_return_pct"] == 20.0


def test_negative_return_recorded_correctly():
    _insert_rec_at("MSFT", days_ago=100, price=200.0)
    fake_close = lambda t, d: 180.0
    ow.run_backfill_once(close_fn=fake_close)
    r = db.get_recommendations("MSFT")[0]
    assert r["outcome_1m_return_pct"] == -10.0
    assert r["outcome_3m_return_pct"] == -10.0


def test_backfill_is_idempotent():
    _insert_rec_at("AAPL", days_ago=100, price=100.0)
    fake_close = lambda t, d: 115.0

    s1 = ow.run_backfill_once(close_fn=fake_close)
    s2 = ow.run_backfill_once(close_fn=fake_close)

    # Second run finds nothing left to fill
    assert s1["horizons_filled"] == 2
    assert s2["horizons_filled"] == 0


def test_close_fetch_failure_skips_silently():
    _insert_rec_at("FAIL", days_ago=100, price=50.0)
    fake_close = lambda t, d: None
    summary = ow.run_backfill_once(close_fn=fake_close)
    assert summary["horizons_filled"] == 0
    r = db.get_recommendations("FAIL")[0]
    assert r["outcome_1m_return_pct"] is None


def test_calibration_summary_buckets_by_recommendation_and_conviction():
    # 3 BUYs (1 winner at 3m, 1 loser, 1 pending)
    _insert_rec_at("AAA", days_ago=100, price=100.0, rec_text="BUY", conviction="HIGH")
    _insert_rec_at("BBB", days_ago=100, price=100.0, rec_text="BUY", conviction="MEDIUM")
    _insert_rec_at("CCC", days_ago=5,   price=100.0, rec_text="BUY", conviction="HIGH")  # pending
    # 1 SELL winner
    _insert_rec_at("DDD", days_ago=100, price=100.0, rec_text="SELL", conviction="HIGH")

    # AAA → +20%, BBB → -10%, DDD → -15% (SELL win)
    prices = {"AAA": 120.0, "BBB": 90.0, "DDD": 85.0}
    ow.run_backfill_once(close_fn=lambda t, d: prices.get(t, 100.0))

    summary = ow.calibration_summary()
    assert summary["total"] == 4
    assert summary["with_3m_outcome"] == 3  # CCC still pending

    buy = summary["by_recommendation"]["BUY"]
    assert buy["n"] == 3
    assert buy["n_with_3m"] == 2
    assert buy["win_rate_3m"] == 0.5  # 1 of 2 BUYs positive at 3m
    assert buy["avg_3m_return"] == 5.0  # (20 + -10) / 2

    sell = summary["by_recommendation"]["SELL"]
    assert sell["win_rate_3m"] == 1.0
    assert sell["avg_3m_return"] == -15.0

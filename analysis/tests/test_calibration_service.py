from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import calibration_service as svc
import app as _app
import db


@pytest.fixture(autouse=True)
def clean_tables():
    conn = db.get_connection()
    try:
        for table in ("recommendations", "research_reports", "tool_result_cache"):
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


def _set_created_at(rec_id, created_at):
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE recommendations SET created_at = ? WHERE id = ?",
            (created_at.isoformat(), rec_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_dashboard_surfaces_due_reviews_and_model_groups():
    db.save_research_report(
        "rep-1",
        "NVDA",
        {"verdict": {"recommendation": "BUY", "conviction": "HIGH"}},
        [],
        llm_provider="gemini",
        llm_model="gemini-2.5-pro",
    )
    reviewed_id = db.save_recommendation("rep-1", "NVDA", "BUY", "HIGH", 100.0)
    db.update_recommendation_outcome(reviewed_id, outcome_1m=12.0)

    due_id = db.save_recommendation("missing-report", "AMD", "AVOID", "LOW", 80.0)
    _set_created_at(due_id, datetime.now() - timedelta(days=70))

    dashboard = svc.get_dashboard(limit=10)

    assert dashboard["summary"]["total_recommendations"] == 2
    assert dashboard["summary"]["reviewed"] == 1
    assert dashboard["summary"]["due_for_review"] == 1
    assert dashboard["summary"]["favorable_rate"] == 100.0
    assert [r["ticker"] for r in dashboard["review_queue"]] == ["AMD"]
    assert dashboard["by_model"][0]["key"] in {"gemini:gemini-2.5-pro", "unknown:unknown"}


def test_update_outcome_is_manual_and_preserves_recommendation_detail():
    rec_id = db.save_recommendation(
        "rep-1",
        "NVDA",
        "BUY",
        "MEDIUM",
        100.0,
        thesis_summary="Demand durable",
    )

    updated = svc.update_outcome(
        rec_id,
        outcome_1m=4.25,
        thesis_falsified=False,
        notes="Still on track after earnings",
    )

    assert updated["id"] == rec_id
    assert updated["outcome_1m_return_pct"] == 4.25
    assert updated["outcome_thesis_falsified"] == 0
    assert updated["thesis_summary"] == "Demand durable"
    assert updated["review_status"] == "reviewed"


def test_refresh_due_outcomes_uses_pull_price_tool():
    rec_id = db.save_recommendation("rep-1", "NVDA", "BUY", "HIGH", 100.0)
    _set_created_at(rec_id, datetime(2024, 1, 1, 9, 30))

    calls = []

    class FakePriceTool:
        def execute(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                error=None,
                data={
                    "bars": [
                        {"time": "2024-01-15T00:00:00", "close": 105.0},
                        {"time": "2024-02-01T00:00:00", "close": 112.0},
                    ]
                },
            )

    result = svc.refresh_due_outcomes(
        recommendation_ids=[rec_id],
        as_of=datetime(2024, 2, 5),
        price_tool=FakePriceTool(),
    )

    assert calls == [{"ticker": "NVDA", "range": "5y"}]
    assert result["updated"] == 1
    refreshed = db.get_recommendations("NVDA")[0]
    assert refreshed["outcome_1m_return_pct"] == 12.0
    assert refreshed["outcome_3m_return_pct"] is None


def test_calibration_dashboard_endpoint(client):
    rec_id = db.save_recommendation("rep-1", "NVDA", "BUY", "MEDIUM", 100.0)

    res = client.post(
        f"/api/recommendations/{rec_id}/outcome",
        json={"outcome_1m_return_pct": 3.5, "outcome_thesis_falsified": "false"},
    )
    assert res.status_code == 200
    assert res.get_json()["recommendation"]["outcome_1m_return_pct"] == 3.5

    dashboard = client.get("/api/calibration/dashboard?ticker=NVDA").get_json()
    assert dashboard["ticker"] == "NVDA"
    assert dashboard["summary"]["reviewed"] == 1

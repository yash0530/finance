"""
Tests for the v2 DB additions: Living Memo, tool log, recommendations,
catalysts, tool cache, sector classification, monitoring.

These tests use the temp HOME set in conftest.py so we never touch the user's
real database.
"""
from datetime import datetime, timedelta

import pytest

import db


@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe v2 tables before each test for isolation."""
    conn = db.get_connection()
    try:
        for table in (
            "living_memo", "living_memo_versions", "tool_call_log",
            "recommendations", "catalysts", "tool_result_cache",
            "sector_classification_cache", "monitoring_digest",
            "monitoring_enabled",
        ):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()
    yield


# ── Living Memo ─────────────────────────────────────────────────────────

def test_save_and_load_living_memo():
    content = {"identity": "GPU maker", "moat": "CUDA ecosystem"}
    v = db.save_living_memo(
        ticker="NVDA",
        content_md="# NVDA\n\nGPU maker.",
        content_json=content,
        delta_summary="Initial memo",
        source_report_id="rep-1",
    )
    assert v == 1

    memo = db.get_living_memo("NVDA")
    assert memo["ticker"] == "NVDA"
    assert memo["current_version"] == 1
    assert memo["content_json"]["identity"] == "GPU maker"


def test_memo_versioning_increments():
    db.save_living_memo("NVDA", "v1", {"k": 1})
    db.save_living_memo("NVDA", "v2", {"k": 2}, delta_summary="updated k")
    db.save_living_memo("NVDA", "v3", {"k": 3})
    memo = db.get_living_memo("NVDA")
    assert memo["current_version"] == 3
    assert memo["content_md"] == "v3"

    versions = db.get_memo_versions("NVDA")
    assert [v["version"] for v in versions] == [3, 2, 1]
    assert versions[1]["delta_summary"] == "updated k"


def test_get_memo_version_by_number():
    db.save_living_memo("NVDA", "v1 content", {"k": "v1"})
    db.save_living_memo("NVDA", "v2 content", {"k": "v2"})
    v1 = db.get_memo_version("NVDA", 1)
    assert v1["content_md"] == "v1 content"
    assert v1["content_json"]["k"] == "v1"

    missing = db.get_memo_version("NVDA", 99)
    assert missing is None


def test_get_living_memo_returns_none_when_missing():
    assert db.get_living_memo("NOTEXIST") is None


# ── Tool call log ───────────────────────────────────────────────────────

def test_log_and_retrieve_tool_calls():
    db.log_tool_call(
        report_id="rep-1", tool_name="fundamentals",
        args={"ticker": "NVDA"},
        result_summary="market_cap=2.1T",
        sources=[{"tool": "fundamentals", "field": "market_cap"}],
        confidence="high", cost_usd=0.0, latency_ms=120,
    )
    db.log_tool_call(
        report_id="rep-1", tool_name="sentiment",
        args={"ticker": "NVDA"}, confidence="medium", cost_usd=0.01,
    )
    log = db.get_tool_call_log("rep-1")
    assert len(log) == 2
    assert log[0]["tool_name"] == "fundamentals"
    assert log[0]["args"]["ticker"] == "NVDA"
    assert log[0]["sources"][0]["field"] == "market_cap"
    assert log[1]["tool_name"] == "sentiment"


def test_tool_log_handles_errors():
    db.log_tool_call(
        report_id="rep-err", tool_name="transcripts",
        error="API timeout", confidence="low", latency_ms=5000,
    )
    log = db.get_tool_call_log("rep-err")
    assert len(log) == 1
    assert log[0]["error"] == "API timeout"


# ── Recommendations + outcomes ──────────────────────────────────────────

def test_save_recommendation_returns_id():
    rid = db.save_recommendation(
        report_id="rep-1", ticker="NVDA",
        recommendation="BUY", conviction="MEDIUM",
        price_at_recommendation=875.42,
        target_low=950, target_high=1100, stop_loss=792,
        thesis_summary="AI demand strong",
        what_would_change_mind="gross margin <70%",
    )
    assert rid > 0
    recs = db.get_recommendations("NVDA")
    assert len(recs) == 1
    assert recs[0]["recommendation"] == "BUY"
    assert recs[0]["target_low"] == 950


def test_update_recommendation_outcome_partial():
    rid = db.save_recommendation(
        "rep-1", "NVDA", "BUY", "HIGH", 100.0,
    )
    # First update: just 1m return
    db.update_recommendation_outcome(rid, outcome_1m=5.5)
    rec = db.get_recommendations("NVDA")[0]
    assert rec["outcome_1m_return_pct"] == 5.5
    assert rec["outcome_3m_return_pct"] is None

    # Second update: add 3m + notes, preserve 1m
    db.update_recommendation_outcome(
        rid, outcome_3m=12.0, thesis_falsified=False,
        notes="On track post Q1 earnings",
    )
    rec = db.get_recommendations("NVDA")[0]
    assert rec["outcome_1m_return_pct"] == 5.5  # preserved
    assert rec["outcome_3m_return_pct"] == 12.0
    assert rec["outcome_thesis_falsified"] == 0
    assert "post Q1" in rec["outcome_notes"]


def test_get_recommendations_filters_by_ticker():
    db.save_recommendation("r1", "NVDA", "BUY", "HIGH", 100.0)
    db.save_recommendation("r2", "AMD", "HOLD", "LOW", 80.0)
    assert len(db.get_recommendations("NVDA")) == 1
    assert len(db.get_recommendations("AMD")) == 1
    assert len(db.get_recommendations()) == 2  # all


# ── Catalysts ───────────────────────────────────────────────────────────

def test_upsert_and_get_catalysts():
    future = (datetime.now() + timedelta(days=14)).date().isoformat()
    far_future = (datetime.now() + timedelta(days=200)).date().isoformat()
    past = (datetime.now() - timedelta(days=5)).date().isoformat()

    db.upsert_catalyst("NVDA", "earnings", future, "Q1 earnings", "yfinance")
    db.upsert_catalyst("NVDA", "earnings", far_future, "Q2 earnings", "yfinance")
    db.upsert_catalyst("NVDA", "earnings", past, "Q4 earnings", "yfinance")
    db.upsert_catalyst("AMD", "earnings", future, "AMD Q1", "yfinance")

    cats = db.get_catalysts(days_ahead=90)
    # Past events filtered, far-future filtered
    assert len(cats) == 2
    tickers = sorted({c["ticker"] for c in cats})
    assert tickers == ["AMD", "NVDA"]


def test_get_catalysts_filtered_by_ticker():
    future = (datetime.now() + timedelta(days=14)).date().isoformat()
    db.upsert_catalyst("NVDA", "earnings", future, "Q1")
    db.upsert_catalyst("AMD", "earnings", future, "Q1")
    cats = db.get_catalysts(tickers=["NVDA"], days_ahead=90)
    assert len(cats) == 1
    assert cats[0]["ticker"] == "NVDA"


def test_catalyst_upsert_idempotent_on_unique_key():
    future = (datetime.now() + timedelta(days=14)).date().isoformat()
    db.upsert_catalyst("NVDA", "earnings", future, "First")
    db.upsert_catalyst("NVDA", "earnings", future, "Updated description")
    cats = db.get_catalysts(["NVDA"])
    assert len(cats) == 1
    assert cats[0]["description"] == "Updated description"


# ── Tool result cache ───────────────────────────────────────────────────

def test_generic_tool_cache_roundtrip():
    db.save_tool_cache("fundamentals", "NVDA", {"market_cap": 2100000000000})
    cached = db.get_tool_cache("fundamentals", "NVDA", max_age_seconds=3600)
    assert cached["market_cap"] == 2100000000000


def test_generic_tool_cache_expiry():
    db.save_tool_cache("fundamentals", "NVDA", {"v": 1})
    # max_age=0 ⇒ always expired (datetime.now() - fetched is always > 0)
    cached = db.get_tool_cache("fundamentals", "NVDA", max_age_seconds=0)
    assert cached is None


def test_generic_tool_cache_overwrite():
    db.save_tool_cache("fundamentals", "NVDA", {"v": 1})
    db.save_tool_cache("fundamentals", "NVDA", {"v": 2})
    cached = db.get_tool_cache("fundamentals", "NVDA", max_age_seconds=3600)
    assert cached["v"] == 2


# ── Sector classification ──────────────────────────────────────────────

def test_sector_classification_roundtrip():
    db.save_sector_classification("NVDA", "semis", "Semiconductors")
    cls = db.get_sector_classification("NVDA")
    assert cls["sector_key"] == "semis"
    assert cls["gics_industry"] == "Semiconductors"
    assert cls["manual_override"] == 0


def test_sector_manual_override():
    db.save_sector_classification("XYZ", "default", "Unknown")
    db.save_sector_classification("XYZ", "saas", "Software", manual_override=True)
    cls = db.get_sector_classification("XYZ")
    assert cls["sector_key"] == "saas"
    assert cls["manual_override"] == 1


# ── Monitoring ──────────────────────────────────────────────────────────

def test_enable_disable_monitoring():
    db.enable_monitoring("NVDA")
    db.enable_monitoring("AMD")
    assert sorted(db.get_monitored_tickers()) == ["AMD", "NVDA"]
    db.disable_monitoring("AMD")
    assert db.get_monitored_tickers() == ["NVDA"]


def test_monitoring_digest_save_and_fetch():
    today = datetime.now().date().isoformat()
    db.save_monitoring_digest(
        "NVDA", today,
        [{"type": "insider_buy", "msg": "CEO bought 10k shares"}],
    )
    digests = db.get_recent_digests(days=1)
    assert len(digests) == 1
    assert digests[0]["ticker"] == "NVDA"
    assert digests[0]["items"][0]["type"] == "insider_buy"


# ── Research report telemetry persistence ───────────────────────────────

def test_save_and_list_research_report_with_telemetry():
    """Roundtrip: save_research_report with telemetry → get_all_research_reports
    returns total_llm_calls > 0, total_cost_usd > 0, and tool_call_count."""
    import uuid

    report_id = str(uuid.uuid4())
    mock_calls = [
        {"role": "planner", "model": "fake", "cost_usd": 0.01, "latency_ms": 100},
        {"role": "bull", "model": "fake", "cost_usd": 0.05, "latency_ms": 200},
        {"role": "bear", "model": "fake", "cost_usd": 0.05, "latency_ms": 200},
        {"role": "judge", "model": "fake", "cost_usd": 0.10, "latency_ms": 300},
    ]
    report_data = {
        "report_id": report_id,
        "ticker": "NVDA",
        "version": "v2",
        "verdict": {
            "recommendation": "BUY",
            "conviction": "HIGH",
            "target_price_range": {"low": 1000, "high": 1200, "timeframe": "12 months"},
        },
    }

    # Also log some tool calls for this report
    db.log_tool_call(report_id=report_id, tool_name="fundamentals",
                     args={"ticker": "NVDA"}, confidence="high", cost_usd=0.0)
    db.log_tool_call(report_id=report_id, tool_name="sentiment",
                     args={"ticker": "NVDA"}, confidence="medium", cost_usd=0.01)

    db.save_research_report(
        report_id=report_id,
        ticker="NVDA",
        report=report_data,
        llm_conversations=mock_calls,
        llm_provider="gemini",
        llm_model="gemini-2.0-flash",
        total_cost_usd=0.21,
        wall_clock_sec=12.5,
    )

    # Verify via list endpoint
    reports = db.get_all_research_reports(limit=10)
    assert len(reports) >= 1
    r = next(rpt for rpt in reports if rpt["id"] == report_id)
    assert r["total_llm_calls"] == 4
    assert r["total_cost_usd"] == 0.21
    assert r["wall_clock_sec"] == 12.5
    assert r["recommendation"] == "BUY"
    assert r["conviction"] == "HIGH"
    assert r["target_low"] == 1000
    assert r["target_high"] == 1200
    assert r["tool_call_count"] == 2

    # Verify via ticker-specific endpoint
    ticker_reports = db.get_research_reports_for_ticker("NVDA", limit=10)
    tr = next(rpt for rpt in ticker_reports if rpt["id"] == report_id)
    assert tr["total_llm_calls"] == 4
    assert tr["tool_call_count"] == 2
    assert tr["recommendation"] == "BUY"

    # Verify full report fetch still works
    full = db.get_research_report(report_id)
    assert full["report"]["verdict"]["recommendation"] == "BUY"
    assert full["total_llm_calls"] == 4

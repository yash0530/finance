"""
Tests for Living Memo staging operations.
"""
import pytest
import db
import living_memo

@pytest.fixture(autouse=True)
def clean_memo_tables():
    conn = db.get_connection()
    try:
        for t in ("living_memo", "living_memo_versions", "living_memo_staged"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
    finally:
        conn.close()
    yield


def test_db_staged_memo_roundtrip():
    # Verify db level staging works
    ticker = "AAPL"
    content = {"identity": {"content_md": "iPhone maker"}}
    
    # Get absent staged memo
    assert db.get_staged_memo(ticker) is None
    
    # Save staged memo
    db.save_staged_memo(
        ticker=ticker,
        content_json=content,
        delta_summary="Staged draft summary",
        source_report_id="report-123"
    )
    
    staged = db.get_staged_memo(ticker)
    assert staged is not None
    assert staged["ticker"] == "AAPL"
    assert staged["content_json"]["identity"]["content_md"] == "iPhone maker"
    assert staged["delta_summary"] == "Staged draft summary"
    assert staged["source_report_id"] == "report-123"
    assert "staged_at" in staged
    
    # Delete staged memo
    db.delete_staged_memo(ticker)
    assert db.get_staged_memo(ticker) is None


def test_living_memo_staging_helpers():
    ticker = "MSFT"
    content = living_memo.empty_memo()
    content["identity"]["content_md"] = "Cloud and AI platform"
    
    # Save staged via helper
    living_memo.save_staged(
        ticker=ticker,
        content_json=content,
        delta_summary="Azure expansion",
        source_report_id="report-msft-1"
    )
    
    staged = living_memo.get_staged(ticker)
    assert staged is not None
    assert staged["content_json"]["identity"]["content_md"] == "Cloud and AI platform"
    assert staged["delta_summary"] == "Azure expansion"
    
    # Discard staged helper
    living_memo.discard_staged(ticker)
    assert living_memo.get_staged(ticker) is None


def test_accept_staged_workflow():
    ticker = "GOOGL"
    content = living_memo.empty_memo()
    content["identity"]["content_md"] = "Search and advertising giant"
    content["moat"]["content_md"] = "Android, YouTube, Search scale"
    
    # 1. Save to staged
    living_memo.save_staged(
        ticker=ticker,
        content_json=content,
        delta_summary="Initial staged release",
        source_report_id="report-goog-1"
    )
    
    # Ensure active living memo does not exist yet
    assert living_memo.load(ticker) is None
    
    # 2. Accept staged
    version = living_memo.accept_staged(ticker)
    assert version == 1
    
    # 3. Verify it is now in active table
    active = living_memo.load(ticker)
    assert active is not None
    assert active["current_version"] == 1
    assert active["content_json"]["identity"]["content_md"] == "Search and advertising giant"
    
    # Verify version details in version history table
    v_history = living_memo.history(ticker)
    assert len(v_history) == 1
    assert v_history[0]["version"] == 1
    assert v_history[0]["delta_summary"] == "Initial staged release"
    assert v_history[0]["source_report_id"] == "report-goog-1"
    
    # 4. Verify staged entry is deleted
    assert living_memo.get_staged(ticker) is None


def test_accept_staged_raises_on_missing():
    with pytest.raises(ValueError) as excinfo:
        living_memo.accept_staged("AMZN")
    assert "No staged memo found for ticker AMZN" in str(excinfo.value)

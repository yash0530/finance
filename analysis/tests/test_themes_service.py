"""
Tests for themes_service + db theme CRUD + idempotent seeding.
"""
from __future__ import annotations

import pytest

import db
import themes_service
from seed_themes import seed_default_themes, DEFAULT_THEMES


@pytest.fixture(autouse=True)
def _wipe_themes():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM theme_tickers")
        conn.execute("DELETE FROM themes")
        conn.commit()
    finally:
        conn.close()
    yield


def test_upsert_and_get_theme():
    db.upsert_theme("test-theme", "Test Theme", "desc")
    db.add_theme_ticker("test-theme", "nvda")
    db.add_theme_ticker("test-theme", "AMD", 2.0)

    detail = themes_service.get_theme_detail("test-theme")
    assert detail["name"] == "Test Theme"
    tickers = {t["ticker"] for t in detail["tickers"]}
    assert tickers == {"NVDA", "AMD"}


def test_themes_for_ticker():
    db.upsert_theme("a", "A")
    db.upsert_theme("b", "B")
    db.add_theme_ticker("a", "NVDA")
    db.add_theme_ticker("b", "NVDA")
    db.add_theme_ticker("b", "AMD")

    themes = themes_service.themes_for_ticker("NVDA")
    slugs = {t["slug"] for t in themes}
    assert slugs == {"a", "b"}


def test_scan_universe_dedupes_with_extra():
    db.upsert_theme("a", "A")
    db.add_theme_ticker("a", "NVDA")
    db.add_theme_ticker("a", "AMD")
    universe = themes_service.scan_universe(extra=["NVDA", "TSM"])
    assert sorted(universe) == ["AMD", "NVDA", "TSM"]


def test_remove_ticker_and_delete_theme():
    db.upsert_theme("a", "A")
    db.add_theme_ticker("a", "NVDA")
    db.add_theme_ticker("a", "AMD")
    db.remove_theme_ticker("a", "NVDA")
    assert {t["ticker"] for t in db.get_theme_tickers("a")} == {"AMD"}
    db.delete_theme("a")
    assert db.get_theme("a") is None
    assert db.get_theme_tickers("a") == []


def test_seed_is_idempotent_and_preserves_edits():
    seed_default_themes()
    themes = db.get_themes()
    assert len(themes) == len(DEFAULT_THEMES)
    ai = themes_service.get_theme_detail("ai-infra")
    assert "NVDA" in {t["ticker"] for t in ai["tickers"]}

    # User edit: remove a ticker, then re-seed — edit must survive.
    db.remove_theme_ticker("ai-infra", "NVDA")
    seed_default_themes()
    ai = themes_service.get_theme_detail("ai-infra")
    assert "NVDA" not in {t["ticker"] for t in ai["tickers"]}
    # Count of themes unchanged
    assert len(db.get_themes()) == len(DEFAULT_THEMES)


def test_theme_ticker_count_in_list():
    db.upsert_theme("a", "A")
    db.add_theme_ticker("a", "NVDA")
    db.add_theme_ticker("a", "AMD")
    themes = {t["slug"]: t for t in themes_service.list_themes()}
    assert themes["a"]["ticker_count"] == 2

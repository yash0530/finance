"""
Tests for seed_screeners — idempotent default screener presets.

Uses the isolated test DB (HOME is redirected by conftest).
"""
from __future__ import annotations

import db
import seed_screeners


def _clear():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM screener_saved")
        conn.commit()
    finally:
        conn.close()


def test_seed_creates_all_presets():
    _clear()
    seed_screeners.seed_default_screeners()
    saved = db.get_screener_saved()
    assert len(saved) == len(seed_screeners.DEFAULT_SCREENERS)
    names = {s["name"] for s in saved}
    assert "Oversold S&P Large Caps" in names
    assert "Pattern: Head & Shoulders (S&P)" in names


def test_seed_is_idempotent():
    _clear()
    seed_screeners.seed_default_screeners()
    n1 = len(db.get_screener_saved())
    seed_screeners.seed_default_screeners()
    assert len(db.get_screener_saved()) == n1  # no duplicates on re-run


def test_seed_recreates_missing_preset():
    # Consistent with seed_themes: a default whose name is absent is re-created
    # on the next seed pass. Deletions are not tracked (these are starter packs).
    _clear()
    seed_screeners.seed_default_screeners()
    victim = next(s for s in db.get_screener_saved() if s["name"] == "Momentum Leaders (S&P)")
    db.delete_screener(victim["id"])
    seed_screeners.seed_default_screeners()
    names = {s["name"] for s in db.get_screener_saved()}
    assert "Momentum Leaders (S&P)" in names


def test_stored_spec_is_runnable_shape():
    _clear()
    seed_screeners.seed_default_screeners()
    by_name = {s["name"]: s for s in db.get_screener_saved()}
    hs = by_name["Pattern: Head & Shoulders (S&P)"]
    assert hs["rules"]["universe"] == "sp500"
    assert hs["rules"]["scan"] is True
    assert hs["rules"]["rules"][0]["field"] == "pattern"

    fast = by_name["52-Week Highs (S&P)"]
    assert "scan" not in fast["rules"]  # fast snapshot preset, no live scan

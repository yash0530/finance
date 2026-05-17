#!/usr/bin/env python3
"""
outcome_worker.py — daily backfill of recommendation outcomes.

For every row in the `recommendations` table:
  • Compute days elapsed since `created_at`.
  • For each horizon (30 / 90 / 180 / 365 days), if the corresponding
    `outcome_Xm_return_pct` is NULL AND enough time has passed, fetch the
    close price closest to the target date via yfinance and store
    return_pct = (price_then − price_at_rec) / price_at_rec * 100.

We do NOT auto-fill `outcome_thesis_falsified` — that's a judgment call
the user makes, and we don't want noisy heuristics polluting the
calibration record. The endpoint /api/advisor/calibration computes
aggregate stats so the user can eyeball where the model is mis-calibrated.

Designed to run once per day; safe to invoke multiple times (idempotent
because we only fill NULL outcomes).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SEC = 60 * 60 * 24  # daily
_RUNNING = False
_THREAD: Optional[threading.Thread] = None

HORIZONS = [
    ("outcome_1m_return_pct", 30),
    ("outcome_3m_return_pct", 90),
    ("outcome_6m_return_pct", 180),
    ("outcome_1y_return_pct", 365),
]


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(ts)
        return d.replace(tzinfo=None) if d.tzinfo else d
    except Exception:
        return None


def _close_near(ticker: str, target_date: datetime) -> Optional[float]:
    """Return the close price on the trading day at or just after `target_date`.

    Fetches a small window around the target. Returns None on failure.
    """
    try:
        import yfinance as yf
    except Exception as e:
        logger.warning("yfinance import failed: %s", e)
        return None

    start = (target_date - timedelta(days=3)).date()
    end = (target_date + timedelta(days=7)).date()

    try:
        hist = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat())
    except Exception as e:
        logger.warning("history fetch failed for %s: %s", ticker, e)
        return None

    if hist is None or hist.empty:
        return None

    # First close ON or AFTER the target date.
    after = hist.loc[hist.index.date >= target_date.date()]
    if not after.empty:
        return float(after.iloc[0]["Close"])
    # Fallback: last close before target_date (handles bleeding-edge horizons)
    before = hist.loc[hist.index.date < target_date.date()]
    if not before.empty:
        return float(before.iloc[-1]["Close"])
    return None


def _compute_return_pct(price_then: float, price_at_rec: float) -> Optional[float]:
    if not price_at_rec or price_at_rec <= 0:
        return None
    return (price_then - price_at_rec) / price_at_rec * 100.0


def backfill_one(rec: Dict, close_fn=None) -> Dict[str, float]:
    """Backfill any due horizons for a single recommendation row.

    Args:
        rec: row from `db.get_recommendations()`
        close_fn: optional override (ticker, datetime) → float. Lets tests
            avoid hitting yfinance.

    Returns:
        Dict of {column_name: return_pct} for newly-filled outcomes.
    """
    close_fn = close_fn or _close_near

    ticker = (rec.get("ticker") or "").upper()
    price_at_rec = float(rec.get("price_at_recommendation") or 0.0)
    created = _parse_iso(rec.get("created_at", ""))
    if not ticker or price_at_rec <= 0 or not created:
        return {}

    now = datetime.now()
    elapsed_days = (now - created).days
    filled: Dict[str, float] = {}

    for col, horizon_days in HORIZONS:
        if elapsed_days < horizon_days:
            continue
        if rec.get(col) is not None:
            continue
        target = created + timedelta(days=horizon_days)
        price_then = close_fn(ticker, target)
        if price_then is None:
            continue
        ret = _compute_return_pct(price_then, price_at_rec)
        if ret is None:
            continue
        filled[col] = round(ret, 2)

    return filled


def _persist_filled(rec_id: int, filled: Dict[str, float]) -> None:
    if not filled:
        return
    import db
    db.update_recommendation_outcome(
        rec_id=rec_id,
        outcome_1m=filled.get("outcome_1m_return_pct"),
        outcome_3m=filled.get("outcome_3m_return_pct"),
        outcome_6m=filled.get("outcome_6m_return_pct"),
        outcome_1y=filled.get("outcome_1y_return_pct"),
        thesis_falsified=None,
        notes="auto-filled by outcome_worker",
    )


def run_backfill_once(close_fn=None) -> Dict:
    """Run a single backfill pass. Returns summary stats."""
    import db
    recs = db.get_recommendations(limit=5000)
    updated = 0
    horizons_filled = 0
    errors = 0

    for rec in recs:
        try:
            filled = backfill_one(rec, close_fn=close_fn)
            if filled:
                _persist_filled(rec["id"], filled)
                updated += 1
                horizons_filled += len(filled)
        except Exception as e:
            errors += 1
            logger.exception("outcome_worker: failed for rec %s: %s", rec.get("id"), e)

    return {
        "recommendations_scanned": len(recs),
        "recommendations_updated": updated,
        "horizons_filled": horizons_filled,
        "errors": errors,
    }


def calibration_summary() -> Dict:
    """Aggregate stats over completed outcomes.

    Returns:
        {
          "total": int,
          "with_3m": int, "with_1y": int,
          "by_recommendation": {
            "BUY": {"n": int, "avg_3m_return": float|None, "win_rate_3m": float|None, ...},
            "HOLD": {...}, "SELL": {...}
          },
          "by_conviction": { "HIGH": {...}, "MEDIUM": {...}, "LOW": {...} },
          "tracked_only": True   # local-provider verdicts are never persisted
        }
    """
    import db
    recs = db.get_recommendations(limit=10000)

    def bucket():
        return {
            "n": 0,
            "n_with_3m": 0, "n_with_1y": 0,
            "sum_3m": 0.0, "sum_1y": 0.0,
            "wins_3m": 0, "wins_1y": 0,
        }

    by_rec: Dict[str, Dict] = {}
    by_conv: Dict[str, Dict] = {}

    for r in recs:
        rec_t = (r.get("recommendation") or "").upper() or "UNKNOWN"
        conv_t = (r.get("conviction") or "").upper() or "UNKNOWN"
        by_rec.setdefault(rec_t, bucket())["n"] += 1
        by_conv.setdefault(conv_t, bucket())["n"] += 1

        r3 = r.get("outcome_3m_return_pct")
        r1y = r.get("outcome_1y_return_pct")

        for b in (by_rec[rec_t], by_conv[conv_t]):
            if r3 is not None:
                b["n_with_3m"] += 1
                b["sum_3m"] += r3
                if (rec_t == "BUY" and r3 > 0) or (rec_t == "SELL" and r3 < 0) or (rec_t == "HOLD" and abs(r3) < 10):
                    b["wins_3m"] += 1
            if r1y is not None:
                b["n_with_1y"] += 1
                b["sum_1y"] += r1y
                if (rec_t == "BUY" and r1y > 0) or (rec_t == "SELL" and r1y < 0) or (rec_t == "HOLD" and abs(r1y) < 15):
                    b["wins_1y"] += 1

    def finalize(b: Dict) -> Dict:
        return {
            "n": b["n"],
            "avg_3m_return": round(b["sum_3m"] / b["n_with_3m"], 2) if b["n_with_3m"] else None,
            "avg_1y_return": round(b["sum_1y"] / b["n_with_1y"], 2) if b["n_with_1y"] else None,
            "win_rate_3m": round(b["wins_3m"] / b["n_with_3m"], 3) if b["n_with_3m"] else None,
            "win_rate_1y": round(b["wins_1y"] / b["n_with_1y"], 3) if b["n_with_1y"] else None,
            "n_with_3m": b["n_with_3m"],
            "n_with_1y": b["n_with_1y"],
        }

    total = len(recs)
    with_3m = sum(1 for r in recs if r.get("outcome_3m_return_pct") is not None)
    with_1y = sum(1 for r in recs if r.get("outcome_1y_return_pct") is not None)

    return {
        "total": total,
        "with_3m_outcome": with_3m,
        "with_1y_outcome": with_1y,
        "by_recommendation": {k: finalize(v) for k, v in by_rec.items()},
        "by_conviction": {k: finalize(v) for k, v in by_conv.items()},
        "tracked_only": True,
    }


def _worker_loop() -> None:
    logger.info("outcome_worker: started (daily)")
    while _RUNNING:
        try:
            summary = run_backfill_once()
            logger.info("outcome_worker: %s", summary)
        except Exception as e:
            logger.exception("outcome_worker: cycle failed: %s", e)
        for _ in range(_POLL_INTERVAL_SEC):
            if not _RUNNING:
                break
            time.sleep(1)
    logger.info("outcome_worker: stopped")


def start_background_worker() -> None:
    global _RUNNING, _THREAD
    if _RUNNING:
        return
    _RUNNING = True
    _THREAD = threading.Thread(target=_worker_loop, daemon=True, name="outcome-worker")
    _THREAD.start()


def stop_background_worker() -> None:
    global _RUNNING, _THREAD
    _RUNNING = False
    if _THREAD:
        _THREAD.join(timeout=5)
        _THREAD = None

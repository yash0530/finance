#!/usr/bin/env python3
"""
monitoring_worker.py — Hourly thesis-decay monitor.

For each holding with a recent Deep Research recommendation, this worker:
  1. Pulls the latest `what_would_change_mind` criteria from the rec
  2. Snapshots recent sentiment/news for the ticker
  3. Asks a cheap LLM ('monitor' task type → fast model) whether anything
     in the new information plausibly triggers a WWCM criterion
  4. Persists DECAYED items (and only those) to `monitoring_digest` for
     today's date, deduping per ticker+severity so a position can't bloat
     the digest with the same signal across hourly runs.

Use cases:
  - Background mode: `start_background_worker()` runs hourly until stopped.
  - On-demand: `run_digest_once()` does a single pass and returns the items.

Both paths share `_process_ticker()`. The endpoints in `app.py`
(`/api/advisor/run-digest`, `/api/advisor/digest`) drive the on-demand path.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date, datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SEC = 3600  # hourly
_RUNNING = False
_THREAD: Optional[threading.Thread] = None

# Recommendations older than this are skipped — the WWCM is presumed stale.
_REC_MAX_AGE_DAYS = 60

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def _today_iso() -> str:
    return date.today().isoformat()


def _now_iso() -> str:
    return datetime.now().isoformat()


def _rec_age_days(rec: Dict) -> Optional[int]:
    try:
        ts = datetime.fromisoformat(rec.get("created_at", ""))
        return (datetime.now() - ts.replace(tzinfo=None) if ts.tzinfo else datetime.now() - ts).days
    except Exception:
        return None


def _latest_rec_by_ticker(tickers: List[str]) -> Dict[str, Dict]:
    """Return ticker→most-recent recommendation for the given tickers."""
    import db
    out: Dict[str, Dict] = {}
    rows = db.get_recommendations(limit=1000)
    wanted = {t.upper() for t in tickers}
    for r in rows:
        t = (r.get("ticker") or "").upper()
        if t in wanted and t not in out:
            out[t] = r
    return out


def _dedup_against_existing(
    ticker: str,
    new_item: Dict,
    existing_items: List[Dict],
) -> Optional[Dict]:
    """Return the item to persist, or None if a stronger/equal signal already exists.

    A new signal is kept only if it is strictly more severe than the most recent
    signal for the same ticker on the same day.
    """
    if not new_item.get("decayed"):
        return None

    new_rank = SEVERITY_RANK.get(new_item.get("severity", "low"), 0)
    for existing in existing_items:
        if existing.get("ticker") != ticker:
            continue
        if not existing.get("decayed"):
            continue
        existing_rank = SEVERITY_RANK.get(existing.get("severity", "low"), 0)
        if existing_rank >= new_rank:
            return None
    return new_item


def _fetch_sentiment_snapshot(ticker: str) -> Optional[Dict]:
    """Best-effort sentiment snapshot. Returns None on failure."""
    try:
        from sentiment_service import get_composite_sentiment
        return get_composite_sentiment(ticker)
    except Exception as e:
        logger.warning("monitoring_worker: sentiment fetch failed for %s: %s", ticker, e)
        return None


def _process_ticker(ticker: str, rec: Dict) -> Optional[Dict]:
    """Run the decay check for one ticker. Returns the digest item or None."""
    from llm_service import check_thesis_decay

    age = _rec_age_days(rec)
    if age is not None and age > _REC_MAX_AGE_DAYS:
        logger.info("monitoring_worker: skip %s, rec is %dd old", ticker, age)
        return None

    sentiment = _fetch_sentiment_snapshot(ticker)
    result = check_thesis_decay(rec, sentiment_snapshot=sentiment)

    item = {
        "ticker": ticker,
        "report_id": rec.get("report_id"),
        "recommendation": rec.get("recommendation"),
        "conviction": rec.get("conviction"),
        "decayed": bool(result.get("decayed", False)),
        "severity": result.get("severity", "low"),
        "signal_summary": result.get("signal_summary", ""),
        "triggered_criteria": result.get("triggered_criteria", []),
        "evidence_summary": result.get("evidence_summary", ""),
        "sentiment_label": (sentiment or {}).get("label"),
        "sentiment_score": (sentiment or {}).get("score"),
        "rec_age_days": age,
        "checked_at": _now_iso(),
    }
    if result.get("error"):
        item["error"] = result["error"]
    return item


def _persist_digest_item(ticker: str, item: Dict) -> bool:
    """Append `item` to today's digest for `ticker`, deduping by severity.

    Returns True if the item was actually written (i.e. survived dedup).
    """
    import db
    today = _today_iso()

    existing = []
    for d in db.get_recent_digests(days=1):
        if d.get("ticker", "").upper() == ticker.upper() and d.get("digest_date") == today:
            existing = d.get("items", [])
            break

    keep = _dedup_against_existing(ticker, item, existing)
    if keep is None:
        return False

    new_items = existing + [keep]
    db.save_monitoring_digest(ticker, today, new_items)
    return True


def _holdings_tickers() -> List[str]:
    """Tickers to monitor. Prefers `monitoring_enabled`, falls back to holdings."""
    import db
    enabled = db.get_monitored_tickers()
    if enabled:
        return enabled
    try:
        return [h["ticker"] for h in db.get_holdings()]
    except Exception:
        return []


def run_digest_once(only_decayed: bool = True) -> List[Dict]:
    """Run a single digest pass across all monitored tickers.

    Args:
        only_decayed: if True (default), return only items where decayed=True.
            Non-decayed items are not persisted either way (the digest table
            is a feed of signals, not a heartbeat).

    Returns:
        List of digest items (potentially empty).
    """
    tickers = _holdings_tickers()
    if not tickers:
        logger.info("monitoring_worker: no monitored tickers")
        return []

    recs = _latest_rec_by_ticker(tickers)
    if not recs:
        logger.info("monitoring_worker: no recommendations on file for %d tickers", len(tickers))
        return []

    items: List[Dict] = []
    for ticker, rec in recs.items():
        try:
            item = _process_ticker(ticker, rec)
        except Exception as e:
            logger.exception("monitoring_worker: error processing %s: %s", ticker, e)
            continue
        if not item:
            continue
        if item.get("decayed"):
            written = _persist_digest_item(ticker, item)
            if written:
                items.append(item)
        elif not only_decayed:
            items.append(item)

    return items


def _worker_loop() -> None:
    logger.info("monitoring_worker: started (interval=%ds)", _POLL_INTERVAL_SEC)
    while _RUNNING:
        try:
            written = run_digest_once()
            if written:
                logger.info("monitoring_worker: wrote %d decay signal(s)", len(written))
        except Exception as e:
            logger.exception("monitoring_worker: cycle failed: %s", e)

        for _ in range(_POLL_INTERVAL_SEC):
            if not _RUNNING:
                break
            time.sleep(1)
    logger.info("monitoring_worker: stopped")


def start_background_worker() -> None:
    global _RUNNING, _THREAD
    if _RUNNING:
        return
    _RUNNING = True
    _THREAD = threading.Thread(target=_worker_loop, daemon=True, name="monitoring-worker")
    _THREAD.start()


def stop_background_worker() -> None:
    global _RUNNING, _THREAD
    _RUNNING = False
    if _THREAD:
        _THREAD.join(timeout=5)
        _THREAD = None

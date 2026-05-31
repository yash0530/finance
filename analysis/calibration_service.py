#!/usr/bin/env python3
"""
Pull-based recommendation calibration.

This module restores the useful V2 calibration loop without workers. It only
reads existing research/recommendation tables unless the caller explicitly
marks or refreshes outcomes.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import db


HORIZONS: Tuple[Tuple[str, int, str], ...] = (
    ("1m", 1, "outcome_1m_return_pct"),
    ("3m", 3, "outcome_3m_return_pct"),
    ("6m", 6, "outcome_6m_return_pct"),
    ("1y", 12, "outcome_1y_return_pct"),
)

# Sizing governor — enforces the house rule "conservative sizing until
# calibration is earned" in code, not just docs. The Judge's raw size is only
# trusted once a conviction tier has a real, favorable resolved track record.
GOVERNOR_CONSERVATIVE_CAP_PCT = 2.0   # ceiling while a tier is unproven
GOVERNOR_MIN_RESOLVED = 5             # resolved calls needed before size is "earned"
GOVERNOR_FAVORABLE_THRESHOLD = 0.5    # favorable rate needed to lift the cap


def list_recommendations(
    ticker: Optional[str] = None,
    limit: int = 100,
    recommendation_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """Return recommendations enriched with report/provider metadata."""
    limit = max(1, min(int(limit or 100), 1000))
    params: List[Any] = []
    where: List[str] = []

    if ticker:
        where.append("r.ticker = ?")
        params.append(ticker.upper().strip())

    if recommendation_ids:
        ids = [int(x) for x in recommendation_ids]
        placeholders = ",".join("?" for _ in ids)
        where.append(f"r.id IN ({placeholders})")
        params.extend(ids)

    sql = """
        SELECT
            r.*,
            rr.llm_provider,
            rr.llm_model,
            rr.total_cost_usd,
            rr.wall_clock_sec,
            rr.generated_at AS report_generated_at,
            s.judge_size_pct,
            s.governed_size_pct,
            s.governor_reason
        FROM recommendations r
        LEFT JOIN research_reports rr ON rr.id = r.report_id
        LEFT JOIN recommendation_sizing s ON s.rec_id = r.id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.created_at DESC LIMIT ?"
    params.append(limit)

    conn = db.get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_decorate_recommendation(dict(row)) for row in rows]
    finally:
        conn.close()


def get_dashboard(ticker: Optional[str] = None, limit: int = 500) -> Dict[str, Any]:
    """Build a calibration dashboard from saved recommendation outcomes."""
    recs = list_recommendations(ticker=ticker, limit=limit)
    summary = _summary(recs)

    return {
        "ticker": ticker.upper().strip() if ticker else None,
        "summary": summary,
        "review_queue": [r for r in recs if r["review_status"] == "due"],
        "recent": recs[:50],
        "by_conviction": _group_stats(recs, "conviction"),
        "by_recommendation": _group_stats(recs, "recommendation"),
        "by_model": _group_stats(recs, "model_key"),
        "horizons": [h[0] for h in HORIZONS],
        "generated_at": datetime.now().isoformat(),
    }


def govern_size(
    conviction: str,
    judge_size_pct: Optional[float],
    recs: Optional[Sequence[Dict[str, Any]]] = None,
) -> Tuple[Optional[float], str]:
    """Cap the Judge's position size by the earned track record at this conviction.

    Returns (governed_size_pct, reason). Reason is empty when nothing is capped.
    The rule: a conviction tier earns its raw size only after
    GOVERNOR_MIN_RESOLVED resolved calls AND a favorable rate at/above
    GOVERNOR_FAVORABLE_THRESHOLD. Until then size is capped to
    GOVERNOR_CONSERVATIVE_CAP_PCT. Sizes already at/under the cap pass through.
    """
    if judge_size_pct is None:
        return None, ""
    if judge_size_pct <= GOVERNOR_CONSERVATIVE_CAP_PCT:
        return judge_size_pct, ""

    tier = (conviction or "").upper() or "LOW"
    if recs is None:
        recs = list_recommendations(limit=1000)
    resolved = [
        r for r in recs
        if (r.get("conviction") or "").upper() == tier and r.get("favorable") is not None
    ]
    n = len(resolved)
    cap = GOVERNOR_CONSERVATIVE_CAP_PCT

    if n < GOVERNOR_MIN_RESOLVED:
        return cap, (
            f"Only {n} resolved {tier} call(s); capped to {cap:.0f}% "
            f"until calibration is earned ({GOVERNOR_MIN_RESOLVED} needed)."
        )

    favorable_rate = sum(1 for r in resolved if r.get("favorable")) / n
    if favorable_rate < GOVERNOR_FAVORABLE_THRESHOLD:
        return cap, (
            f"{tier} calls favorable only {favorable_rate * 100:.0f}% over {n} resolved; "
            f"capped to {cap:.0f}% until edge is demonstrated."
        )

    # Edge demonstrated — trust the Judge's size.
    return judge_size_pct, ""


def update_outcome(
    recommendation_id: int,
    outcome_1m: Optional[float] = None,
    outcome_3m: Optional[float] = None,
    outcome_6m: Optional[float] = None,
    outcome_1y: Optional[float] = None,
    thesis_falsified: Optional[bool] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Manually mark an outcome. This is the primary calibration write path."""
    db.update_recommendation_outcome(
        recommendation_id,
        outcome_1m=outcome_1m,
        outcome_3m=outcome_3m,
        outcome_6m=outcome_6m,
        outcome_1y=outcome_1y,
        thesis_falsified=thesis_falsified,
        notes=notes,
    )
    updated = list_recommendations(recommendation_ids=[recommendation_id], limit=1)
    if not updated:
        raise ValueError(f"Recommendation {recommendation_id} not found")
    return updated[0]


def refresh_due_outcomes(
    recommendation_ids: Optional[Sequence[int]] = None,
    as_of: Optional[datetime] = None,
    price_tool: Any = None,
) -> Dict[str, Any]:
    """Pull current price history and fill due, missing horizon returns.

    This is intentionally user-triggered. It uses the existing price_history
    Tool, so data fetching stays inside the Tool layer and remains cited.
    """
    now = as_of or datetime.now()
    recs = list_recommendations(
        limit=1000,
        recommendation_ids=recommendation_ids,
    )
    due = [r for r in recs if _due_missing_fields(r, now)]
    if not due:
        return {"updated": 0, "checked": len(recs), "errors": [], "recommendations": []}

    tool = price_tool or _get_price_history_tool()
    updated: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    bars_by_ticker: Dict[str, List[Dict[str, Any]]] = {}

    for rec in due:
        ticker = rec["ticker"]
        if ticker not in bars_by_ticker:
            result = tool.execute(ticker=ticker, range="5y")
            if getattr(result, "error", None):
                errors.append({"ticker": ticker, "error": result.error})
                bars_by_ticker[ticker] = []
            else:
                bars_by_ticker[ticker] = (result.data or {}).get("bars") or []

        bars = bars_by_ticker.get(ticker) or []
        fields = _compute_due_returns(rec, bars, now)
        if not fields:
            continue

        db.update_recommendation_outcome(
            rec["id"],
            outcome_1m=fields.get("outcome_1m_return_pct"),
            outcome_3m=fields.get("outcome_3m_return_pct"),
            outcome_6m=fields.get("outcome_6m_return_pct"),
            outcome_1y=fields.get("outcome_1y_return_pct"),
            notes="Pull refresh from price_history",
        )
        refreshed = list_recommendations(recommendation_ids=[rec["id"]], limit=1)
        if refreshed:
            updated.append(refreshed[0])

    return {
        "updated": len(updated),
        "checked": len(recs),
        "errors": errors,
        "recommendations": updated,
    }


def _get_price_history_tool():
    from tools import get_tool

    tool = get_tool("price_history")
    if not tool:
        raise RuntimeError("price_history tool is not registered")
    return tool


def _decorate_recommendation(row: Dict[str, Any]) -> Dict[str, Any]:
    row["model_key"] = _model_key(row)
    row["created_at_days_old"] = _days_old(row.get("created_at"))
    row["review_status"] = _review_status(row)
    row["favorable"] = _is_favorable(row)
    return row


def _summary(recs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    reviewed = [r for r in recs if _has_any_outcome(r)]
    due = [r for r in recs if r.get("review_status") == "due"]
    favorable = [r for r in reviewed if r.get("favorable") is not None]
    falsified = [
        r for r in reviewed
        if r.get("outcome_thesis_falsified") is not None
    ]

    return {
        "total_recommendations": len(recs),
        "reviewed": len(reviewed),
        "due_for_review": len(due),
        "unreviewed": max(0, len(recs) - len(reviewed)),
        "favorable_rate": _pct(sum(1 for r in favorable if r["favorable"]), len(favorable)),
        "thesis_falsified_rate": _pct(
            sum(1 for r in falsified if bool(r.get("outcome_thesis_falsified"))),
            len(falsified),
        ),
        "avg_1m_return_pct": _avg(r.get("outcome_1m_return_pct") for r in recs),
        "avg_3m_return_pct": _avg(r.get("outcome_3m_return_pct") for r in recs),
        "avg_6m_return_pct": _avg(r.get("outcome_6m_return_pct") for r in recs),
        "avg_1y_return_pct": _avg(r.get("outcome_1y_return_pct") for r in recs),
    }


def _group_stats(recs: Sequence[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in recs:
        buckets[str(rec.get(key) or "unknown")].append(rec)

    out = []
    for name, items in buckets.items():
        stats = _summary(items)
        out.append({"key": name, **stats})
    return sorted(out, key=lambda x: (-x["total_recommendations"], x["key"]))


def _review_status(rec: Dict[str, Any], now: Optional[datetime] = None) -> str:
    if _due_missing_fields(rec, now or datetime.now()):
        return "due"
    if _has_any_outcome(rec):
        return "reviewed"
    return "not_due"


def _due_missing_fields(rec: Dict[str, Any], now: datetime) -> List[str]:
    created = _parse_dt(rec.get("created_at"))
    if not created:
        return []
    due = []
    for _label, months, field in HORIZONS:
        if rec.get(field) is None and now >= _add_months(created, months):
            due.append(field)
    return due


def _compute_due_returns(
    rec: Dict[str, Any],
    bars: Sequence[Dict[str, Any]],
    now: datetime,
) -> Dict[str, float]:
    created = _parse_dt(rec.get("created_at"))
    start_price = _float_or_none(rec.get("price_at_recommendation"))
    if not created or not start_price:
        return {}

    fields: Dict[str, float] = {}
    for _label, months, field in HORIZONS:
        if rec.get(field) is not None:
            continue
        target_date = _add_months(created, months)
        if now < target_date:
            continue
        close = _nearest_close_on_or_after(bars, target_date)
        if close is None:
            continue
        fields[field] = round(((close - start_price) / start_price) * 100, 2)
    return fields


def _nearest_close_on_or_after(
    bars: Sequence[Dict[str, Any]],
    target_date: datetime,
) -> Optional[float]:
    best: Optional[Tuple[datetime, float]] = None
    for bar in bars:
        ts = _parse_dt(bar.get("time"))
        close = _float_or_none(bar.get("close"))
        if not ts or close is None or ts.date() < target_date.date():
            continue
        if best is None or ts < best[0]:
            best = (ts, close)
    return best[1] if best else None


def _has_any_outcome(rec: Dict[str, Any]) -> bool:
    return any(rec.get(field) is not None for _label, _months, field in HORIZONS)


def _is_favorable(rec: Dict[str, Any]) -> Optional[bool]:
    outcome = (
        rec.get("outcome_3m_return_pct")
        if rec.get("outcome_3m_return_pct") is not None
        else rec.get("outcome_1m_return_pct")
    )
    if outcome is None:
        return None

    action = (rec.get("recommendation") or "").upper()
    if action == "BUY":
        return outcome > 0
    if action in {"TRIM", "AVOID", "SELL"}:
        return outcome < 0
    if action == "HOLD":
        return abs(outcome) <= 2.5
    return None


def _model_key(rec: Dict[str, Any]) -> str:
    provider = rec.get("llm_provider") or "unknown"
    model = rec.get("llm_model") or "unknown"
    return f"{provider}:{model}"


def _avg(values: Iterable[Any]) -> Optional[float]:
    nums = [_float_or_none(v) for v in values]
    nums = [v for v in nums if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def _pct(count: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round((count / total) * 100, 1)


def _days_old(value: Any) -> Optional[int]:
    dt = _parse_dt(value)
    if not dt:
        return None
    return (datetime.now() - dt).days


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    days = [31, 29 if _is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(dt.day, days[month - 1])
    return dt.replace(year=year, month=month, day=day)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

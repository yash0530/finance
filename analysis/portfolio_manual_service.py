#!/usr/bin/env python3
"""
Manual portfolio service.

Pull-based CRUD and summaries over the existing portfolio_holdings table.
No broker sync, credentials, background workers, or destructive migrations.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import db


TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
MANUAL_SOURCES = {"manual", "manual_csv"}


class PortfolioValidationError(ValueError):
    pass


def _now() -> str:
    return datetime.now().isoformat()


def normalize_ticker(ticker: Any) -> str:
    value = str(ticker or "").upper().strip()
    if not TICKER_RE.match(value):
        raise PortfolioValidationError("ticker must be a valid symbol")
    return value


def _float_or_none(value: Any, field: str) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise PortfolioValidationError(f"{field} must be numeric") from exc
    if parsed < 0:
        raise PortfolioValidationError(f"{field} cannot be negative")
    return parsed


def _positive_float(value: Any, field: str) -> float:
    parsed = _float_or_none(value, field)
    if parsed is None or parsed <= 0:
        raise PortfolioValidationError(f"{field} must be greater than zero")
    return parsed


def _row_to_holding(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "shares": row["shares"],
        "avg_cost": row["avg_cost"],
        "source": row["source"] or "manual",
        "synced_at": row["synced_at"],
    }


def list_holdings() -> List[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT id, ticker, shares, avg_cost, source, synced_at
               FROM portfolio_holdings
               ORDER BY ticker, id"""
        ).fetchall()
        return [_row_to_holding(row) for row in rows]
    finally:
        conn.close()


def get_holding(holding_id: int) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    try:
        row = conn.execute(
            """SELECT id, ticker, shares, avg_cost, source, synced_at
               FROM portfolio_holdings
               WHERE id = ?""",
            (holding_id,),
        ).fetchone()
        return _row_to_holding(row) if row else None
    finally:
        conn.close()


def create_holding(payload: Dict[str, Any], source: str = "manual") -> Dict[str, Any]:
    ticker = normalize_ticker(payload.get("ticker"))
    shares = _positive_float(payload.get("shares"), "shares")
    avg_cost = _float_or_none(payload.get("avg_cost"), "avg_cost")
    clean_source = source if source in MANUAL_SOURCES else "manual"

    conn = db.get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO portfolio_holdings (ticker, shares, avg_cost, source, synced_at)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker, shares, avg_cost, clean_source, _now()),
        )
        conn.commit()
        return get_holding(int(cur.lastrowid))
    finally:
        conn.close()


def update_holding(holding_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    existing = get_holding(holding_id)
    if not existing:
        return None

    ticker = normalize_ticker(payload.get("ticker", existing["ticker"]))
    shares = _positive_float(payload.get("shares", existing["shares"]), "shares")
    avg_cost = _float_or_none(payload.get("avg_cost", existing["avg_cost"]), "avg_cost")

    conn = db.get_connection()
    try:
        conn.execute(
            """UPDATE portfolio_holdings
               SET ticker = ?, shares = ?, avg_cost = ?, source = ?, synced_at = ?
               WHERE id = ?""",
            (ticker, shares, avg_cost, existing["source"] or "manual", _now(), holding_id),
        )
        conn.commit()
        return get_holding(holding_id)
    finally:
        conn.close()


def delete_holding(holding_id: int) -> bool:
    conn = db.get_connection()
    try:
        cur = conn.execute("DELETE FROM portfolio_holdings WHERE id = ?", (holding_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _fetch_quotes(tickers: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    from tools.movers import fetch_quotes
    return fetch_quotes(list(tickers))


def _aggregate_by_ticker(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for h in holdings:
        ticker = h["ticker"]
        entry = grouped.setdefault(ticker, {
            "ticker": ticker,
            "shares": 0.0,
            "cost_basis": 0.0,
            "cost_shares": 0.0,
            "lots": 0,
            "sources": set(),
        })
        shares = float(h["shares"] or 0)
        avg_cost = h.get("avg_cost")
        entry["shares"] += shares
        entry["lots"] += 1
        entry["sources"].add(h.get("source") or "manual")
        if avg_cost is not None:
            entry["cost_basis"] += shares * float(avg_cost)
            entry["cost_shares"] += shares

    out = []
    for item in grouped.values():
        cost_shares = item.pop("cost_shares")
        item["avg_cost"] = item["cost_basis"] / cost_shares if cost_shares else None
        item["sources"] = sorted(item["sources"])
        out.append(item)
    return sorted(out, key=lambda x: x["ticker"])


def summary(include_quotes: bool = True) -> Dict[str, Any]:
    holdings = list_holdings()
    positions = _aggregate_by_ticker(holdings)
    quotes: Dict[str, Dict[str, Any]] = {}
    quote_error = None
    if include_quotes and positions:
        try:
            quotes = _fetch_quotes([p["ticker"] for p in positions])
        except Exception as exc:
            quote_error = str(exc)

    total_cost_basis = 0.0
    total_position_value = 0.0
    known_market_value = 0.0
    known_unrealized_gain = 0.0
    known_unrealized_basis = 0.0
    source_exposure = defaultdict(float)
    theme_exposure = defaultdict(float)

    for p in positions:
        q = quotes.get(p["ticker"], {}) if quotes else {}
        price = q.get("price")
        cost_basis = float(p.get("cost_basis") or 0)
        current_value = float(p["shares"]) * float(price) if price is not None else cost_basis
        unrealized_gain = (current_value - cost_basis) if price is not None and cost_basis else None
        unrealized_gain_pct = (unrealized_gain / cost_basis * 100) if unrealized_gain is not None and cost_basis else None

        p.update({
            "price": price,
            "change_pct": q.get("change_pct"),
            "current_value": current_value,
            "unrealized_gain": unrealized_gain,
            "unrealized_gain_pct": unrealized_gain_pct,
        })

        total_cost_basis += cost_basis
        total_position_value += current_value
        if price is not None:
            known_market_value += current_value
            known_unrealized_gain += current_value - cost_basis
            known_unrealized_basis += cost_basis

        themes = db.get_themes_for_ticker(p["ticker"])
        if themes:
            for theme in themes:
                theme_exposure[theme["name"]] += current_value
        else:
            theme_exposure["Unmapped"] += current_value

    for h in holdings:
        q = quotes.get(h["ticker"], {}) if quotes else {}
        price = q.get("price")
        shares = float(h.get("shares") or 0)
        avg_cost = h.get("avg_cost")
        lot_value = shares * float(price) if price is not None else shares * float(avg_cost or 0)
        source_exposure[h.get("source") or "manual"] += lot_value

    for p in positions:
        p["weight_pct"] = (p["current_value"] / total_position_value * 100) if total_position_value else 0

    return {
        "holdings": holdings,
        "positions": positions,
        "count": len(holdings),
        "position_count": len(positions),
        "total_cost_basis": total_cost_basis,
        "total_position_value": total_position_value,
        "known_market_value": known_market_value,
        "known_unrealized_gain": known_unrealized_gain if known_unrealized_basis else None,
        "known_unrealized_gain_pct": (
            known_unrealized_gain / known_unrealized_basis * 100
            if known_unrealized_basis else None
        ),
        "source_exposure": dict(sorted(source_exposure.items())),
        "theme_exposure": dict(sorted(theme_exposure.items())),
        "quotes_included": include_quotes,
        "quote_error": quote_error,
        "updated_at": _now(),
    }


def _csv_value(row: Dict[str, Any], *names: str) -> Any:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        if name in lower:
            return lower[name]
    return None


def import_csv(csv_text: str, replace_manual: bool = False) -> Dict[str, Any]:
    if not csv_text or not csv_text.strip():
        raise PortfolioValidationError("csv text required")

    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise PortfolioValidationError("csv must include headers")

    parsed = []
    errors = []
    for line_number, row in enumerate(reader, start=2):
        try:
            ticker = _csv_value(row, "ticker", "symbol")
            shares = _csv_value(row, "shares", "quantity", "qty")
            avg_cost = _csv_value(row, "avg_cost", "average_cost", "cost_basis", "cost")
            parsed.append({
                "ticker": normalize_ticker(ticker),
                "shares": _positive_float(shares, "shares"),
                "avg_cost": _float_or_none(avg_cost, "avg_cost"),
            })
        except PortfolioValidationError as exc:
            errors.append({"line": line_number, "error": str(exc)})

    if errors:
        return {"ok": False, "imported": 0, "errors": errors}

    conn = db.get_connection()
    try:
        if replace_manual:
            placeholders = ",".join("?" for _ in MANUAL_SOURCES)
            conn.execute(
                f"DELETE FROM portfolio_holdings WHERE source IN ({placeholders})",
                tuple(MANUAL_SOURCES),
            )
        now = _now()
        conn.executemany(
            """INSERT INTO portfolio_holdings (ticker, shares, avg_cost, source, synced_at)
               VALUES (:ticker, :shares, :avg_cost, 'manual_csv', :synced_at)""",
            [{**row, "synced_at": now} for row in parsed],
        )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "imported": len(parsed), "errors": []}

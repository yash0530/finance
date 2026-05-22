#!/usr/bin/env python3
"""
rebalancing_engine.py — Portfolio optimization with research citations.

v2 (B2): Joins live holdings against the latest per-ticker Deep Research
recommendation. Mechanical concentration / diversification checks are
preserved, but the headline action for each held ticker is driven by the
research verdict when one exists (BUY → ADD, SELL → EXIT, HOLD → HOLD or
TRIM if mechanically overweight). Each action carries a `research` block
that the UI renders as a citation chip linking back to the report.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

RISK_PROFILES = {
    "conservative": {"max_single": 10.0, "max_sector": 25.0, "min_positions": 15},
    "moderate":     {"max_single": 15.0, "max_sector": 35.0, "min_positions": 10},
    "aggressive":   {"max_single": 25.0, "max_sector": 50.0, "min_positions": 5},
}

STALE_DAYS = 30
URGENCY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _latest_research_by_ticker() -> Dict[str, Dict]:
    """Map ticker → most-recent recommendation row (or {} if DB unavailable)."""
    try:
        import db  # local import keeps this module test-friendly
    except Exception:
        return {}

    try:
        rows = db.get_recommendations(limit=500)
    except Exception as e:
        logger.warning("rebalance: could not fetch recommendations: %s", e)
        return {}

    latest: Dict[str, Dict] = {}
    for r in rows:
        t = (r.get("ticker") or "").upper()
        if not t:
            continue
        # rows come back ordered by created_at DESC, so first wins
        if t not in latest:
            latest[t] = r
    return latest


def _age_days(iso_ts: Optional[str]) -> Optional[int]:
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(iso_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - ts).days)
    except Exception:
        return None


def _research_block(rec: Dict) -> Dict:
    age = _age_days(rec.get("created_at"))
    return {
        "report_id": rec.get("report_id"),
        "recommendation": rec.get("recommendation"),
        "conviction": rec.get("conviction"),
        "thesis_summary": rec.get("thesis_summary") or "",
        "target_low": rec.get("target_low"),
        "target_high": rec.get("target_high"),
        "stop_loss": rec.get("stop_loss"),
        "price_at_recommendation": rec.get("price_at_recommendation"),
        "created_at": rec.get("created_at"),
        "age_days": age,
        "stale": (age is not None and age > STALE_DAYS),
    }


def _holding_weight_pct(h: Dict, total_value: float) -> float:
    if h.get("weight_pct") is not None:
        return float(h["weight_pct"])
    val = float(h.get("current_value") or 0.0)
    return (val / total_value * 100.0) if total_value > 0 else 0.0


def _classify_research_action(
    rec_text: str,
    conviction: str,
    weight_pct: float,
    max_single: float,
) -> tuple[str, str]:
    """Map (recommendation, conviction) → (action, urgency).

    BUY → ADD if not over max, else TRIM (over-concentration overrides BUY).
    SELL → EXIT.
    HOLD → TRIM if overweight, else HOLD.
    """
    rec_u = (rec_text or "").upper()
    conv_u = (conviction or "").upper()

    if "SELL" in rec_u:
        return ("EXIT", "high" if conv_u == "HIGH" else "medium")

    if "BUY" in rec_u:
        if weight_pct > max_single:
            return ("TRIM", "high" if weight_pct > max_single * 1.5 else "medium")
        return ("ADD", "high" if conv_u == "HIGH" else "medium")

    # HOLD / unknown
    if weight_pct > max_single:
        return ("TRIM", "high" if weight_pct > max_single * 1.5 else "medium")
    return ("HOLD", "low")


def analyze_portfolio(
    holdings: List[Dict],
    profile: str = "moderate",
    research_overrides: Optional[Dict[str, Dict]] = None,
) -> Dict:
    """Analyze holdings against a risk profile + latest research recommendations.

    Args:
        holdings: enriched holdings (must include `ticker`; ideally `current_value`,
            `weight_pct`, `unrealized_pnl_pct`).
        profile: 'conservative' | 'moderate' | 'aggressive'.
        research_overrides: optional ticker→rec dict; if None, fetched from DB.
            Tests pass this directly to avoid DB writes.

    Returns:
        {
          "profile": str, "rules": dict,
          "issues": [...],
          "actions": [ { action, ticker, reason, urgency, source,
                         current_weight_pct, unrealized_pnl_pct, research } ],
          "research_coverage": {"with_research": int, "without_research": int}
        }
    """
    if profile not in RISK_PROFILES:
        profile = "moderate"
    rules = RISK_PROFILES[profile]

    issues: List[Dict] = []
    actions: List[Dict] = []

    if not holdings:
        return {
            "profile": profile, "rules": rules,
            "issues": [], "actions": [],
            "research_coverage": {"with_research": 0, "without_research": 0},
        }

    total_value = sum(float(h.get("current_value") or 0.0) for h in holdings)
    research = research_overrides if research_overrides is not None else _latest_research_by_ticker()

    with_research = 0
    without_research = 0

    # Per-ticker decisions (research-driven where possible)
    for h in holdings:
        ticker = (h.get("ticker") or "").upper()
        if not ticker:
            continue

        weight_pct = _holding_weight_pct(h, total_value)
        pnl_pct = h.get("unrealized_pnl_pct")
        rec = research.get(ticker)

        if rec:
            with_research += 1
            action, urgency = _classify_research_action(
                rec.get("recommendation", ""),
                rec.get("conviction", ""),
                weight_pct,
                rules["max_single"],
            )
            rblock = _research_block(rec)

            # Build reason
            conv_txt = (rec.get("conviction") or "").lower() or "unknown"
            rec_txt = (rec.get("recommendation") or "").upper() or "—"
            if action == "EXIT":
                reason = (
                    f"Research verdict: {rec_txt} ({conv_txt} conviction). "
                    f"Exit position."
                )
            elif action == "TRIM" and "BUY" in rec_txt:
                reason = (
                    f"Bullish research ({rec_txt}, {conv_txt}) but {weight_pct:.1f}% "
                    f"weight exceeds {rules['max_single']}% cap. Trim to size."
                )
            elif action == "TRIM":
                reason = (
                    f"{weight_pct:.1f}% weight exceeds {rules['max_single']}% cap "
                    f"and research is {rec_txt} ({conv_txt})."
                )
            elif action == "ADD":
                reason = (
                    f"Research verdict: {rec_txt} ({conv_txt} conviction). "
                    f"Current weight {weight_pct:.1f}% has room under "
                    f"{rules['max_single']}% cap."
                )
            else:  # HOLD
                reason = f"Research verdict: HOLD ({conv_txt} conviction). No action."

            if rblock["stale"]:
                reason += f"  Research is {rblock['age_days']}d old — refresh before acting."

            actions.append({
                "action": action,
                "ticker": ticker,
                "reason": reason,
                "urgency": urgency,
                "source": "research",
                "current_weight_pct": round(weight_pct, 2),
                "unrealized_pnl_pct": pnl_pct,
                "research": rblock,
            })

            if weight_pct > rules["max_single"]:
                issues.append({"type": "overweight", "ticker": ticker, "pct": weight_pct})
        else:
            without_research += 1
            # No research → mechanical-only rules
            if weight_pct > rules["max_single"]:
                issues.append({"type": "overweight", "ticker": ticker, "pct": weight_pct})
                urgency = "high" if weight_pct > rules["max_single"] * 1.5 else "medium"
                actions.append({
                    "action": "TRIM",
                    "ticker": ticker,
                    "reason": (
                        f"{weight_pct:.1f}% weight exceeds {rules['max_single']}% cap "
                        f"for {profile} profile. No research on file — run Deep Research "
                        f"to confirm thesis before trimming."
                    ),
                    "urgency": urgency,
                    "source": "mechanical",
                    "current_weight_pct": round(weight_pct, 2),
                    "unrealized_pnl_pct": pnl_pct,
                    "research": None,
                })
            elif pnl_pct is not None and pnl_pct < -20.0:
                actions.append({
                    "action": "REVIEW",
                    "ticker": ticker,
                    "reason": (
                        f"Down {pnl_pct:.1f}% with no research on file. Run Deep Research "
                        f"to decide between averaging down and cutting losses."
                    ),
                    "urgency": "high" if pnl_pct < -35.0 else "medium",
                    "source": "mechanical",
                    "current_weight_pct": round(weight_pct, 2),
                    "unrealized_pnl_pct": pnl_pct,
                    "research": None,
                })

    # Portfolio-level: under-diversified
    if len(holdings) < rules["min_positions"]:
        issues.append({
            "type": "underdiversified",
            "count": len(holdings),
            "min": rules["min_positions"],
        })
        actions.append({
            "action": "ADD",
            "ticker": None,
            "reason": (
                f"Only {len(holdings)} positions — {profile} profile recommends at "
                f"least {rules['min_positions']}. Consider adding researched names."
            ),
            "urgency": "low",
            "source": "mechanical",
            "current_weight_pct": None,
            "unrealized_pnl_pct": None,
            "research": None,
        })

    actions.sort(key=lambda x: URGENCY_ORDER.get(x["urgency"], 3))

    return {
        "profile": profile,
        "rules": rules,
        "issues": issues,
        "actions": actions,
        "research_coverage": {
            "with_research": with_research,
            "without_research": without_research,
        },
    }

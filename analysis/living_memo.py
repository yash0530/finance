"""
living_memo.py — Per-ticker evolving knowledge document (Phase 3).

A Living Memo is the agent's persistent knowledge of one ticker, stored as
structured JSON (10 named sections) plus rendered markdown. New versions
accumulate in `living_memo_versions`; the head sits in `living_memo`.

This module is a thin, well-typed facade over the DB layer in `db.py` plus
helpers for rendering, diffing, and extracting planner-relevant fields
(open_questions, falsifiability conditions).

Lower-level storage is in db.py:
  - db.get_living_memo
  - db.save_living_memo
  - db.get_memo_versions
  - db.get_memo_version
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import db


# ============================================================================
# Schema
# ============================================================================

# The 10 canonical sections (order is the rendering order)
MEMO_SECTIONS: List[str] = [
    "identity",
    "moat",
    "long_term_thesis",
    "current_state",
    "management_track_record",
    "risk_register",
    "open_questions",
    "recent_observations",
    "past_verdicts",
    "anti_thesis",
]

# Human-readable section titles for rendering
SECTION_TITLES: Dict[str, str] = {
    "identity": "Identity",
    "moat": "Moat",
    "long_term_thesis": "Long-term Thesis",
    "current_state": "Current State",
    "management_track_record": "Management Track Record",
    "risk_register": "Risk Register",
    "open_questions": "Open Questions",
    "recent_observations": "Recent Observations",
    "past_verdicts": "Past Verdicts",
    "anti_thesis": "Anti-thesis",
}

# Sections whose `structured` payload is a *list* (e.g. risk rows, verdict rows)
# rather than a dict. Important for typing of empty skeletons + diffs.
_LIST_STRUCTURED_SECTIONS = {"risk_register", "past_verdicts"}


# ============================================================================
# Skeleton + load helpers
# ============================================================================

def _empty_section(name: str) -> Dict[str, Any]:
    """Build a fresh empty section. `structured` is a list for the
    list-shaped sections and a dict elsewhere."""
    return {
        "content_md": "",
        "structured": [] if name in _LIST_STRUCTURED_SECTIONS else {},
        "last_updated": "",
        "evidence_refs": [],
        "confidence": "low",
    }


def empty_memo() -> Dict[str, Any]:
    """Return an empty memo skeleton with all 10 sections present."""
    return {name: _empty_section(name) for name in MEMO_SECTIONS}


def load(ticker: str) -> Optional[Dict[str, Any]]:
    """Return the current memo for a ticker, or None if it does not exist.

    Shape: the DB row dict, with `content_json` already parsed.
    """
    return db.get_living_memo(ticker)


def load_or_empty(ticker: str) -> Dict[str, Any]:
    """Return the existing memo's content_json, or a fresh empty skeleton.

    Note this returns the *sections dict*, not the DB-row wrapper — handy for
    code that just wants to read/edit sections.
    """
    memo = load(ticker)
    if not memo:
        return empty_memo()
    content = memo.get("content_json") or {}
    # Ensure every section is present (forward-compatible if schema grows)
    return _ensure_all_sections(content)


def _ensure_all_sections(content: Dict[str, Any]) -> Dict[str, Any]:
    """Return `content` with every canonical section guaranteed to exist."""
    out = dict(content) if isinstance(content, dict) else {}
    for name in MEMO_SECTIONS:
        if name not in out or not isinstance(out.get(name), dict):
            out[name] = _empty_section(name)
        else:
            # Backfill missing fields without overwriting present ones.
            section = dict(out[name])
            defaults = _empty_section(name)
            for k, v in defaults.items():
                section.setdefault(k, v)
            out[name] = section
    return out


# ============================================================================
# Save (versioning) + history
# ============================================================================

def save(
    ticker: str,
    content_json: Dict[str, Any],
    delta_summary: str = "",
    source_report_id: Optional[str] = None,
    user_edited: bool = False,
) -> int:
    """Save a new memo version.

    Computes the markdown via `render()` and forwards to `db.save_living_memo`.
    Returns the new version number (1 for first save, N+1 for subsequent).
    """
    content_json = _ensure_all_sections(content_json)
    content_md = render(content_json, ticker=ticker)
    return db.save_living_memo(
        ticker=ticker,
        content_md=content_md,
        content_json=content_json,
        delta_summary=delta_summary,
        source_report_id=source_report_id,
        user_edited=user_edited,
    )


def history(ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
    """List memo versions for a ticker (newest first)."""
    return db.get_memo_versions(ticker, limit=limit)


def get_version(ticker: str, version: int) -> Optional[Dict[str, Any]]:
    """Get a specific historical memo version."""
    return db.get_memo_version(ticker, version)


# ============================================================================
# Rendering
# ============================================================================

def render(content_json: Dict[str, Any], ticker: str = "") -> str:
    """Convert the section dict into a single markdown document.

    Skips empty sections gracefully so first-pass partial memos render cleanly.
    """
    header = f"# {ticker.upper()} — Living Memo" if ticker else "# Living Memo"
    parts: List[str] = [header, ""]

    for name in MEMO_SECTIONS:
        section = content_json.get(name) or {}
        body = _format_section_body(name, section)
        if not body:
            continue
        title = SECTION_TITLES.get(name, name.replace("_", " ").title())
        parts.append(f"## {title}")
        meta_bits: List[str] = []
        if section.get("confidence"):
            meta_bits.append(f"confidence: {section['confidence']}")
        if section.get("last_updated"):
            meta_bits.append(f"updated: {section['last_updated']}")
        if meta_bits:
            parts.append(f"*{ ' · '.join(meta_bits) }*")
        parts.append("")
        parts.append(body)
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _format_section_body(name: str, section: Dict[str, Any]) -> str:
    """Render the body of a single section as markdown.

    Prefer `content_md`. If empty, fall back to rendering `structured` for the
    list-shaped sections so risk_register / past_verdicts surface even without
    a hand-written paragraph.
    """
    md = (section.get("content_md") or "").strip()
    if md:
        return md

    structured = section.get("structured")
    if name == "risk_register" and isinstance(structured, list) and structured:
        lines = []
        for row in structured:
            if not isinstance(row, dict):
                continue
            risk = row.get("risk") or row.get("name") or "(unnamed risk)"
            sev = row.get("severity", "?")
            prob = row.get("probability", "?")
            mit = row.get("mitigant") or row.get("mitigation") or ""
            trig = row.get("monitoring_trigger") or row.get("trigger") or ""
            line = f"- **{risk}** — severity={sev}, prob={prob}"
            if mit:
                line += f". Mitigant: {mit}"
            if trig:
                line += f". Trigger: {trig}"
            lines.append(line)
        return "\n".join(lines)

    if name == "past_verdicts" and isinstance(structured, list) and structured:
        lines = []
        for row in structured:
            if not isinstance(row, dict):
                continue
            date = row.get("date", "")
            rec = row.get("recommendation", "")
            conv = row.get("conviction", "")
            price = row.get("price_at_recommendation", "")
            outcome = row.get("outcome", "")
            line = f"- {date}: **{rec}** ({conv}) @ ${price}"
            if outcome:
                line += f" → {outcome}"
            lines.append(line)
        return "\n".join(lines)

    return ""


# ============================================================================
# Diffs
# ============================================================================

def section_diff(
    old: Dict[str, Any], new: Dict[str, Any], section: str
) -> Dict[str, Any]:
    """Per-section diff.

    Returns: {"old": <old section>, "new": <new section>,
              "changed": bool, "changes": [str]}
    """
    old_section = (old or {}).get(section) or _empty_section(section)
    new_section = (new or {}).get(section) or _empty_section(section)
    changes: List[str] = []

    old_md = (old_section.get("content_md") or "").strip()
    new_md = (new_section.get("content_md") or "").strip()
    if old_md != new_md:
        if not old_md and new_md:
            changes.append("content added")
        elif old_md and not new_md:
            changes.append("content removed")
        else:
            changes.append("content_md updated")

    if old_section.get("structured") != new_section.get("structured"):
        changes.append("structured data updated")

    if old_section.get("confidence") != new_section.get("confidence"):
        changes.append(
            f"confidence {old_section.get('confidence') or '?'} -> "
            f"{new_section.get('confidence') or '?'}"
        )

    old_refs = list(old_section.get("evidence_refs") or [])
    new_refs = list(new_section.get("evidence_refs") or [])
    if old_refs != new_refs:
        added = [r for r in new_refs if r not in old_refs]
        removed = [r for r in old_refs if r not in new_refs]
        if added:
            changes.append(f"+{len(added)} evidence ref(s)")
        if removed:
            changes.append(f"-{len(removed)} evidence ref(s)")

    return {
        "old": old_section,
        "new": new_section,
        "changed": bool(changes),
        "changes": changes,
    }


def diff_summary(old: Dict[str, Any], new: Dict[str, Any]) -> str:
    """Produce a human-readable summary of what changed across all sections.

    Used as the `delta_summary` on save.
    """
    old = _ensure_all_sections(old or {})
    new = _ensure_all_sections(new or {})
    lines: List[str] = []
    for name in MEMO_SECTIONS:
        d = section_diff(old, new, name)
        if d["changed"]:
            title = SECTION_TITLES.get(name, name)
            lines.append(f"- {title}: {'; '.join(d['changes'])}")
    if not lines:
        return "No material changes."
    return "Changed sections:\n" + "\n".join(lines)


# ============================================================================
# Planner / monitoring extractors
# ============================================================================

def get_open_questions(memo: Dict[str, Any]) -> List[str]:
    """Extract the list of open questions.

    Accepts either a full DB-row memo (`{"content_json": {...}}`) or a raw
    sections dict. Returns a list of question strings, even if the section
    stores them as bulleted markdown or a structured list.
    """
    sections = _coerce_to_sections(memo)
    section = sections.get("open_questions") or {}
    return _extract_string_list(section)


def get_falsifiability_conditions(memo: Dict[str, Any]) -> List[str]:
    """Extract `what_would_change_mind` conditions from the anti_thesis section.

    Used by the monitoring daemon to know which observations should fire a
    decay notification.
    """
    sections = _coerce_to_sections(memo)
    section = sections.get("anti_thesis") or {}
    structured = section.get("structured") or {}

    # Preferred: explicit structured field
    if isinstance(structured, dict):
        wwcm = structured.get("what_would_change_mind")
        if isinstance(wwcm, list):
            return [str(x).strip() for x in wwcm if str(x).strip()]
        if isinstance(wwcm, str) and wwcm.strip():
            return [wwcm.strip()]

    # Fallback: parse bulleted markdown
    return _extract_string_list(section)


def _coerce_to_sections(memo: Dict[str, Any]) -> Dict[str, Any]:
    """Accept either a DB-row memo (with `content_json`) or a sections dict."""
    if not memo:
        return {}
    if "content_json" in memo and isinstance(memo["content_json"], dict):
        return memo["content_json"]
    return memo


def _extract_string_list(section: Dict[str, Any]) -> List[str]:
    """Pull a list of strings out of a section.

    Order of preference: structured (if list), structured["items"], or bullets
    parsed from content_md.
    """
    structured = section.get("structured")
    if isinstance(structured, list):
        return [str(x).strip() for x in structured if str(x).strip()]
    if isinstance(structured, dict):
        items = structured.get("items")
        if isinstance(items, list):
            return [str(x).strip() for x in items if str(x).strip()]

    md = (section.get("content_md") or "").strip()
    if not md:
        return []
    out: List[str] = []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue
        # bullet markers: -, *, +, or numbered "1."
        if line.startswith(("-", "*", "+")):
            out.append(line[1:].strip())
        elif len(line) > 2 and line[0].isdigit() and line[1:3] in (". ", ") "):
            out.append(line[3:].strip())
        else:
            out.append(line)
    return [x for x in out if x]


# ============================================================================
# Convenience: stamping `last_updated` on a section
# ============================================================================

def stamp_section(section: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of `section` with `last_updated` set to now()."""
    out = dict(section)
    out["last_updated"] = datetime.now().isoformat()
    return out


# ============================================================================
# Staging operations
# ============================================================================

def save_staged(
    ticker: str,
    content_json: Dict[str, Any],
    delta_summary: Optional[str] = None,
    source_report_id: Optional[str] = None,
) -> None:
    """Save a new staged memo version to the staging table."""
    content_json = _ensure_all_sections(content_json)
    db.save_staged_memo(
        ticker=ticker,
        content_json=content_json,
        delta_summary=delta_summary,
        source_report_id=source_report_id,
    )


def get_staged(ticker: str) -> Optional[Dict[str, Any]]:
    """Retrieve the staged memo for a ticker, or None if not found."""
    return db.get_staged_memo(ticker)


def accept_staged(ticker: str) -> int:
    """Load the staged memo, save it as the current active version, and delete it from staging."""
    staged = get_staged(ticker)
    if not staged:
        raise ValueError(f"No staged memo found for ticker {ticker}")

    new_version = save(
        ticker=ticker,
        content_json=staged["content_json"],
        delta_summary=staged.get("delta_summary") or "",
        source_report_id=staged.get("source_report_id"),
        user_edited=False,
    )
    discard_staged(ticker)
    return new_version


def discard_staged(ticker: str) -> None:
    """Delete the staged memo for a ticker."""
    db.delete_staged_memo(ticker)

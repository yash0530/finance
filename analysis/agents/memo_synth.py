"""
agents.memo_synth — propose a Living Memo update after a research session.

Inputs: previous memo, the session's EvidenceLedger, the Judge's verdict.
Output: a new memo (full sections dict) + a delta_summary describing what
changed and why.

The agent is intentionally conservative: it preserves prior content where
no new evidence justifies an update, and it cites which tool produced each
material change.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import llm_service
import living_memo

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Memo Synthesizer for a per-ticker Living Memo.

You receive:
  1. The current memo (10 named sections, each with content_md + structured)
  2. New evidence collected during this research session (from tools)
  3. The Judge agent's verdict (recommendation, conviction, key cases)

You produce an updated memo by editing each section conservatively:

  • Update a section ONLY when there is material new evidence or a clear
    shift in the verdict that warrants the change.
  • Preserve prior content verbatim where it is still supported.
  • For each meaningful edit, briefly reference which evidence supports it
    (e.g. "transcripts: NRR 118%", "insider_form4: CFO bought $2M").
  • Never invent facts. If evidence is silent on a section, leave it alone.
  • Keep each section's content_md concise (a few paragraphs or bullets).

The 10 sections are:
  identity, moat, long_term_thesis, current_state, management_track_record,
  risk_register, open_questions, recent_observations, past_verdicts, anti_thesis

Per-section structure:
  {
    "content_md": "<markdown>",
    "structured": {...} or [...],   (lists for risk_register & past_verdicts)
    "last_updated": "<ISO timestamp>" — set when content_md or structured changes,
    "evidence_refs": ["tool_name", ...],
    "confidence": "high" | "medium" | "low"
  }

Return STRICT JSON only — no prose, no markdown fences."""


def synthesize_memo_update(
    ticker: str,
    old_memo: Dict[str, Any],
    evidence_ledger,
    verdict: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the LLM call to propose an updated memo.

    Returns:
        {
          "new_memo": {<sections>},
          "delta_summary": "<one-paragraph summary>",
          "error": "<string>"          # only on failure
        }
    On any failure (LLM unavailable, malformed JSON), returns the old memo
    unchanged with `error` populated so the caller never crashes.
    """
    old_sections = living_memo._ensure_all_sections(
        living_memo._coerce_to_sections(old_memo or {})
    )

    try:
        provider, model = llm_service._get_provider_and_model("analysis")
    except Exception as e:
        logger.warning(f"memo_synth: LLM provider unavailable: {e}")
        return {
            "new_memo": old_sections,
            "delta_summary": "LLM unavailable",
            "error": str(e),
        }

    user_prompt = _build_user_prompt(
        ticker=ticker,
        old_sections=old_sections,
        evidence_summary=_safe_evidence_prompt(evidence_ledger),
        verdict=verdict or {},
    )

    try:
        raw = provider.complete_json(SYSTEM_PROMPT, user_prompt, model)
    except Exception as e:
        logger.warning(f"memo_synth: LLM call failed: {e}")
        return {
            "new_memo": old_sections,
            "delta_summary": "LLM unavailable",
            "error": str(e),
        }

    # _extract_json may return {"error": ..., "raw": ...} on parse failure
    if not isinstance(raw, dict) or raw.get("error"):
        err = raw.get("error", "Failed to parse memo synth response") if isinstance(raw, dict) else "Bad response type"
        logger.warning(f"memo_synth: parse failure: {err}")
        return {
            "new_memo": old_sections,
            "delta_summary": "LLM unavailable",
            "error": str(err),
        }

    new_sections = raw.get("new_memo") or raw.get("memo") or raw.get("sections")
    if not isinstance(new_sections, dict):
        # Some models may return the sections at the top level.
        candidate = {k: v for k, v in raw.items() if k in living_memo.MEMO_SECTIONS}
        if candidate:
            new_sections = candidate
        else:
            return {
                "new_memo": old_sections,
                "delta_summary": "LLM unavailable",
                "error": "Response missing 'new_memo' field",
            }

    new_sections = living_memo._ensure_all_sections(new_sections)
    delta_summary = (
        raw.get("delta_summary")
        or living_memo.diff_summary(old_sections, new_sections)
    )
    return {"new_memo": new_sections, "delta_summary": str(delta_summary)}


# ============================================================================
# Helpers
# ============================================================================

def _safe_evidence_prompt(evidence_ledger) -> str:
    """Render the evidence ledger as a prompt-friendly string, defensively."""
    if evidence_ledger is None:
        return "(no evidence collected this session)"
    try:
        if hasattr(evidence_ledger, "evidence_prompt"):
            text = evidence_ledger.evidence_prompt()
            return text or "(no evidence collected this session)"
        if isinstance(evidence_ledger, str):
            return evidence_ledger
        if isinstance(evidence_ledger, dict):
            return json.dumps(evidence_ledger, default=str, indent=2)[:6000]
    except Exception as e:
        logger.debug(f"evidence_prompt rendering failed: {e}")
    return "(evidence unavailable)"


def _build_user_prompt(
    ticker: str,
    old_sections: Dict[str, Any],
    evidence_summary: str,
    verdict: Dict[str, Any],
) -> str:
    """Compose the user message for the LLM call."""
    old_blob = json.dumps(old_sections, default=str, indent=2)
    verdict_blob = json.dumps(verdict or {}, default=str, indent=2)

    schema_block = _output_schema_block()

    return f"""TICKER: {ticker.upper()}

═══════════ CURRENT MEMO (sections) ═══════════
{old_blob}

═══════════ NEW EVIDENCE (this session) ═══════════
{evidence_summary}

═══════════ VERDICT (Judge agent) ═══════════
{verdict_blob}

═══════════ TASK ═══════════
Produce an updated memo. Update each section only when the new evidence or
verdict materially changes the picture. Preserve unchanged sections verbatim.

For changed sections:
  • Re-write content_md to reflect the new state of knowledge.
  • Reference supporting evidence by tool name in `evidence_refs`.
  • Update `confidence` if your certainty has shifted.
  • The caller will set `last_updated` — you may leave it as-is or blank.

Return STRICT JSON in this shape:
{schema_block}
"""


def _output_schema_block() -> str:
    sections_block = ",\n    ".join(
        f'"{name}": {{ "content_md": "...", "structured": {_default_structured(name)}, '
        f'"evidence_refs": [], "confidence": "low" }}'
        for name in living_memo.MEMO_SECTIONS
    )
    return (
        "{\n"
        '  "new_memo": {\n'
        f"    {sections_block}\n"
        "  },\n"
        '  "delta_summary": "<one-paragraph human-readable summary of what changed and why>"\n'
        "}"
    )


def _default_structured(name: str) -> str:
    return "[]" if name in living_memo._LIST_STRUCTURED_SECTIONS else "{}"

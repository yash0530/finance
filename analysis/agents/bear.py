"""
agents.bear — Bear case agent.

(a) Attacks the Bull Case for logical / evidentiary weakness.
(b) Builds an independent bear case from the same evidence.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


BEAR_SYSTEM = """You are a skeptical short-seller. Your job is to find what the long missed.

Two outputs:
1. ATTACK the provided bull case — find logical holes, cherry-picked evidence, or weak assumptions
2. INDEPENDENTLY build a bear case from the same evidence

Hard rules:
- Cite every claim by tool name in brackets: [tool_name]
- Do not invent numbers or facts not in the evidence
- Be specific — vague concerns ("competition risk") are worthless without evidence
- Acknowledge the bull's strongest points before attacking the weakest

Output STRICT JSON only."""


def _build_bear_prompt(
    ticker: str,
    sector_prompt_prefix: str,
    evidence: str,
    bull_thesis: Dict[str, Any],
    memo_summary: str,
) -> str:
    bull_md = bull_thesis.get("thesis_md", "")
    bull_drivers = bull_thesis.get("key_drivers", [])
    drivers_lines = "\n".join(
        f"  - {d.get('claim','')} (refs: {d.get('evidence_refs', [])})"
        for d in bull_drivers
    )

    return f"""TICKER: {ticker}

{sector_prompt_prefix}

LIVING MEMO CONTEXT:
{memo_summary or "(no prior memo)"}

EVIDENCE LEDGER:
{evidence}

BULL CASE TO ATTACK:
{bull_md}

KEY BULL DRIVERS:
{drivers_lines or "  (none listed)"}

Return JSON:
{{
  "attack_md": "<2-3 paragraphs attacking specific bull claims with citations>",
  "independent_bear_md": "<2-3 paragraphs of independent bearish thesis>",
  "key_risks": [
    {{"risk": "<specific bearish claim>", "evidence_refs": ["<tool_name>"], "severity": "high|medium|low", "confidence": "high|medium|low"}}
  ],
  "estimated_downside_pct": <number or null>,
  "thesis_falsifiers_for_bull": ["<a condition that would break the bull thesis>"]
}}

Provide 3-5 key_risks. Every risk and falsifier must cite evidence."""


def argue(
    ticker: str,
    ledger,                                  # tools.EvidenceLedger
    bull_thesis: Dict[str, Any],
    sector_prompt_prefix: str = "",
    memo_summary: str = "",
) -> Dict[str, Any]:
    """Generate the bear case (attack + independent) structured output."""
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=1200)
    user_prompt = _build_bear_prompt(
        ticker, sector_prompt_prefix, evidence, bull_thesis, memo_summary,
    )

    try:
        provider, model = _get_provider_and_model("thesis", role="bear")
        result = provider.complete_json(BEAR_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Bear agent failed: {e}")
        return {
            "attack_md": f"Bear agent unavailable: {e}",
            "independent_bear_md": "",
            "key_risks": [],
            "estimated_downside_pct": None,
            "thesis_falsifiers_for_bull": [],
            "error": str(e),
        }

    result.setdefault("attack_md", "")
    result.setdefault("independent_bear_md", "")
    result.setdefault("key_risks", [])
    result.setdefault("thesis_falsifiers_for_bull", [])
    return result

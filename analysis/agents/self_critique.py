"""
agents.self_critique — adversarial review of the Judge's verdict.

Finds the weakest 3 claims in the verdict and identifies whether
falsifying evidence is available (or could be fetched). May trigger another
planner round if it surfaces critical gaps.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


CRITIQUE_SYSTEM = """You are a senior risk officer reviewing an investment analyst's verdict.

Your job: find the 3 weakest claims in the verdict, identify what evidence would
falsify each, and assess whether the falsifying evidence is available in the
ledger but was overlooked.

Be ruthless. The point of this step is to catch what the judge missed."""


def _build_critique_prompt(
    ticker: str,
    verdict: Dict[str, Any],
    evidence: str,
) -> str:
    return f"""TICKER: {ticker}

VERDICT TO CRITIQUE:
- Recommendation: {verdict.get('recommendation')} ({verdict.get('conviction')})
- Summary: {verdict.get('summary')}
- Bull case: {[c.get('claim') for c in verdict.get('bull_case', [])]}
- Bear case: {[c.get('claim') for c in verdict.get('bear_case', [])]}
- What would change mind: {verdict.get('what_would_change_mind', [])}

EVIDENCE LEDGER:
{evidence}

Return JSON:
{{
  "weakest_claims": [
    {{
      "claim": "<the weak claim text>",
      "why_weak": "<specific reason>",
      "would_be_falsified_by": "<what evidence>",
      "falsifying_evidence_available": <true if in ledger, false if would need new tools>,
      "suggested_tool_to_fetch": "<tool name or null>"
    }}
  ],
  "should_revise_verdict": <bool — true if any weakest_claim materially undermines the recommendation>,
  "revision_suggestion": "<specific revision, or empty string>",
  "additional_tools_to_call": ["<tool name>", ...]
}}

Provide exactly 3 weakest_claims."""


def critique(
    ticker: str,
    verdict: Dict[str, Any],
    ledger,                                  # tools.EvidenceLedger
) -> Dict[str, Any]:
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=800)
    user_prompt = _build_critique_prompt(ticker, verdict, evidence)

    try:
        provider, model = _get_provider_and_model("analysis", role="self_critique")
        result = provider.complete_json(CRITIQUE_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Self-critique failed: {e}")
        return {
            "weakest_claims": [],
            "should_revise_verdict": False,
            "revision_suggestion": "",
            "additional_tools_to_call": [],
            "error": str(e),
        }

    result.setdefault("weakest_claims", [])
    result.setdefault("should_revise_verdict", False)
    result.setdefault("revision_suggestion", "")
    result.setdefault("additional_tools_to_call", [])
    return result

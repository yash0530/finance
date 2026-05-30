"""
agents.bull_rebuttal — Bull rebuttal agent.

Reads the bull case, bear case/attacks, and the evidence ledger, then argues
against the bear's points to defend the bull thesis.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


BULL_REBUTTAL_SYSTEM = """You are a long-only fundamental analyst defending your thesis.

You receive your original bull case, the bear's attack and independent bear case, and the raw evidence. Your job:
1. Rebut the bear's criticisms of your thesis using ONLY the evidence provided.
2. Acknowledge valid risks but argue why they are mitigated or outweighed by positive drivers.
3. Cite every claim by tool name in brackets: [tool_name]
4. Do not invent numbers or facts not in the evidence.

Output STRICT JSON only."""


def _build_rebuttal_prompt(
    ticker: str,
    sector_prompt_prefix: str,
    evidence: str,
    bull: Dict[str, Any],
    bear: Dict[str, Any],
    memo_summary: str,
) -> str:
    bull_md = bull.get("thesis_md", "")
    bear_md = bear.get("independent_bear_md", "")
    bear_attack = bear.get("attack_md", "")

    return f"""TICKER: {ticker}

{sector_prompt_prefix}

LIVING MEMO CONTEXT:
{memo_summary or "(no prior memo)"}

EVIDENCE LEDGER:
{evidence}

YOUR ORIGINAL BULL CASE:
{bull_md}

BEAR'S ATTACK ON YOUR BULL CASE:
{bear_attack}

INDEPENDENT BEAR CASE:
{bear_md}

Provide a rebuttal to the bear's attacks and independent points. Return JSON:
{{
  "rebuttal_md": "<2-3 paragraphs of rebuttal defending the bull thesis against the bear's points>",
  "key_counterarguments": [
    {{"claim": "<specific counterargument claim>", "evidence_refs": ["<tool_name>"], "mitigation_logic": "<how this mitigates the risk or addresses the bear's attack>"}}
  ]
}}

Constraints:
- Provide 2-4 key_counterarguments
- Every claim must list at least one evidence_ref (a tool name from the ledger)"""


def rebut(
    ticker: str,
    ledger,                                  # tools.EvidenceLedger
    bull: Dict[str, Any],
    bear: Dict[str, Any],
    sector_prompt_prefix: str = "",
    memo_summary: str = "",
) -> Dict[str, Any]:
    """Generate the bull rebuttal structured output."""
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=1200)
    user_prompt = _build_rebuttal_prompt(
        ticker, sector_prompt_prefix, evidence, bull, bear, memo_summary
    )

    try:
        provider, model = _get_provider_and_model("thesis", role="bull_rebuttal")
        result = provider.complete_json(BULL_REBUTTAL_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Bull rebuttal agent failed: {e}")
        return {
            "rebuttal_md": f"Bull rebuttal agent unavailable: {e}",
            "key_counterarguments": [],
            "error": str(e),
        }

    result.setdefault("rebuttal_md", "")
    result.setdefault("key_counterarguments", [])
    return result

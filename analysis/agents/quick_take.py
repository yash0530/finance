"""
agents.quick_take — the cheap /why path.

A single LLM call that reads a small evidence ledger (news + trends + technicals
+ sentiment) and produces a 3-sentence hypothesis for why a ticker is moving.
Citations by tool name, same contract as the debate agents.

Budget/cost is tracked by the caller (agent_loop.run_quick_take) via the active
LLMCallSession — this module never calls a provider outside that flow.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


QUICK_TAKE_SYSTEM = """You are a sharp markets analyst writing a fast read on why a stock is moving.

Write EXACTLY three sentences:
1. The most likely driver of recent price action, cited by tool name in brackets [tool_name].
2. One corroborating or complicating data point, also cited.
3. What you'd watch next to confirm or kill the read.

Rules:
- Use ONLY the evidence provided. Do not invent numbers.
- Cite every factual claim by tool name in brackets.
- Be concrete and specific. No hedging filler.

Output STRICT JSON only."""


def _build_prompt(ticker: str, evidence: str) -> str:
    return f"""TICKER: {ticker}

EVIDENCE LEDGER:
{evidence}

Return JSON:
{{
  "why_md": "<exactly three sentences with [tool_name] citations>",
  "stance": "bullish|bearish|neutral",
  "evidence_refs": ["<tool_name>", "..."]
}}"""


def generate(ticker: str, ledger) -> Dict[str, Any]:
    """Generate a 3-sentence quick take from the evidence ledger."""
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=900)
    user_prompt = _build_prompt(ticker, evidence)

    try:
        provider, model = _get_provider_and_model("analysis", role="quick_take")
        result = provider.complete_json(QUICK_TAKE_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Quick-take agent failed: {e}")
        return {
            "why_md": f"Quick take unavailable: {e}",
            "stance": "neutral",
            "evidence_refs": [],
            "error": str(e),
        }

    result.setdefault("why_md", "")
    result.setdefault("stance", "neutral")
    result.setdefault("evidence_refs", [])
    return result

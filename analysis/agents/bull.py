"""
agents.bull — Bull case agent.

Reads the evidence ledger and builds the strongest possible bullish case for the
ticker, citing evidence by tool name. Output is structured for the Judge agent.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


BULL_SYSTEM = """You are a long-only fundamental analyst who builds the strongest possible bullish case.

Your job: construct the most compelling buy thesis using ONLY the evidence provided.
- Cite every claim by tool name in brackets: [tool_name]
- Do not invent numbers or facts not in the evidence
- It is OK to acknowledge uncertainty, but lead with strength
- Identify the 3-5 most powerful drivers (long-term + catalyst)
- Propose a price target methodology, anchored to evidence
- Explicitly ingest and debate technical indicators (RSI overbought/oversold, MACD momentum, golden/death cross, moving averages, chart patterns from [technicals]) and relative S&P 500 scanner rankings (sector momentum percentiles, forward multiple comparisons, beta rankings, spotlight tags from [sp500_lookup]) in your thesis to justify strong upside timing and context.

Output STRICT JSON only. No prose outside the JSON."""


def _build_bull_prompt(
    ticker: str,
    sector_prompt_prefix: str,
    evidence: str,
    memo_summary: str,
) -> str:
    return f"""TICKER: {ticker}

{sector_prompt_prefix}

LIVING MEMO CONTEXT (prior knowledge):
{memo_summary or "(no prior memo — first analysis)"}

EVIDENCE LEDGER:
{evidence}

Build the bull case. Return JSON:
{{
  "thesis_md": "<2-4 short paragraphs of the bull thesis>",
  "key_drivers": [
    {{"claim": "<specific bullish claim>", "evidence_refs": ["<tool_name>"], "confidence": "high|medium|low"}}
  ],
  "price_target_methodology": "<how you'd value the upside, anchored to specific evidence>",
  "estimated_upside_pct": <number or null>,
  "catalysts": ["<near-term catalyst>", "..."]
}}

Constraints:
- Provide 3-5 key_drivers
- Every claim must list at least one evidence_ref (a tool name from the ledger)
- If evidence is thin, prefer fewer high-confidence drivers over many low-confidence ones"""


def argue(
    ticker: str,
    ledger,                                  # tools.EvidenceLedger
    sector_prompt_prefix: str = "",
    memo_summary: str = "",
) -> Dict[str, Any]:
    """Generate the bull case structured output."""
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=1200)
    user_prompt = _build_bull_prompt(ticker, sector_prompt_prefix, evidence, memo_summary)

    try:
        provider, model = _get_provider_and_model("thesis", role="bull")
        result = provider.complete_json(BULL_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Bull agent failed: {e}")
        return {
            "thesis_md": f"Bull agent unavailable: {e}",
            "key_drivers": [],
            "price_target_methodology": "",
            "estimated_upside_pct": None,
            "catalysts": [],
            "error": str(e),
        }

    # Ensure shape
    result.setdefault("thesis_md", "")
    result.setdefault("key_drivers", [])
    result.setdefault("catalysts", [])
    return result

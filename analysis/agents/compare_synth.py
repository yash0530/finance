"""
agents.compare_synth — cross-ticker comparison synthesizer.

Takes the per-ticker verdicts produced by parallel quick deep-research runs and
produces a ranking plus head-to-head notes. One LLM call. Citations reference
each ticker's verdict by symbol.

Budget/cost is tracked by the caller (console_orchestrator) via the active
LLMCallSession.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


COMPARE_SYSTEM = """You are a portfolio manager ranking competing investment candidates.

You receive each candidate's verdict (recommendation, conviction, summary, key
catalysts, target range). Produce a decisive ranking grounded ONLY in what the
verdicts say.

Rules:
- Rank from most to least attractive for fresh capital over a 12-month horizon.
- Justify each rank with a specific reason drawn from that ticker's verdict.
- Call out the single most important head-to-head difference.
- Be decisive. A ranking that refuses to choose is useless.

Output STRICT JSON only."""


def _summarize_verdict(ticker: str, verdict: Dict[str, Any]) -> str:
    return json.dumps({
        "ticker": ticker,
        "recommendation": verdict.get("recommendation"),
        "conviction": verdict.get("conviction"),
        "summary": (verdict.get("summary") or "")[:600],
        "target_price_range": verdict.get("target_price_range"),
        "key_catalysts": verdict.get("key_catalysts"),
    }, default=str)


def _build_prompt(candidates: List[Dict[str, Any]]) -> str:
    blocks = "\n\n".join(_summarize_verdict(c["ticker"], c["verdict"]) for c in candidates)
    tickers = ", ".join(c["ticker"] for c in candidates)
    return f"""CANDIDATES: {tickers}

PER-TICKER VERDICTS:
{blocks}

Return JSON:
{{
  "ranking": [
    {{"rank": 1, "ticker": "<T>", "reason": "<why it ranks here, citing its verdict>"}}
  ],
  "head_to_head": "<the single most important difference between the top candidates>",
  "winner": "<ticker>",
  "summary_md": "<2-3 sentence comparative take>"
}}"""


def synthesize(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Produce a ranking from a list of {ticker, verdict} dicts."""
    from llm_service import _get_provider_and_model

    valid = [c for c in candidates if c.get("verdict")]
    if not valid:
        return {
            "ranking": [], "head_to_head": "", "winner": None,
            "summary_md": "No verdicts available to compare.",
            "error": "no_verdicts",
        }

    user_prompt = _build_prompt(valid)
    try:
        provider, model = _get_provider_and_model("analysis", role="compare_synth")
        result = provider.complete_json(COMPARE_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"compare_synth failed: {e}")
        return {
            "ranking": [{"rank": i + 1, "ticker": c["ticker"], "reason": "ranking unavailable"}
                        for i, c in enumerate(valid)],
            "head_to_head": "",
            "winner": valid[0]["ticker"],
            "summary_md": f"Comparison synthesis unavailable: {e}",
            "error": str(e),
        }

    result.setdefault("ranking", [])
    result.setdefault("winner", valid[0]["ticker"] if valid else None)
    result.setdefault("summary_md", "")
    return result

"""
agents.judge — Verdict agent.

Reads the bull case, bear case, bull rebuttal, and full evidence ledger, then produces the
final structured verdict including falsifiability conditions and a trade plan.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


JUDGE_SYSTEM = """You are an investment analyst about to allocate real capital for an individual investor.
Operate with disciplined sizing, entry, exit, and risk controls; those matter as much as narrative quality.

You receive a bull case, a bear case, a bull rebuttal defending the thesis, and the raw evidence. Your job:
1. Weigh all inputs and produce a recommendation
2. Set conviction honestly — only HIGH when bull thesis is strong AND bear concerns are well-addressed
3. Define WHAT WOULD CHANGE YOUR MIND — falsifiable, monitorable conditions
4. Produce a trade plan: entry zone, stop methodology, targets, time stop, position size guidance
5. Explicitly weigh and debate technical indicators (RSI overbought/oversold, MACD, golden/death cross, moving averages, chart patterns from [technicals]) and relative S&P 500 scanner rankings (sector momentum, forward multiples vs sector/market, beta rankings, spotlight tags from [sp500_lookup]) to synthesize optimal entry/exit levels and capital fit.

Conviction calibration:
- HIGH: multiple independent supports; bear case addressed with evidence; falsifiability conditions clear and distant
- MEDIUM: thesis reasonable but at least one bear argument partially unresolved, OR key evidence missing
- LOW: significant unresolved questions; flag for further research not capital deployment

Output STRICT JSON only."""


def _build_judge_prompt(
    ticker: str,
    sector_prompt_prefix: str,
    evidence: str,
    bull: Dict[str, Any],
    bear: Dict[str, Any],
    bull_rebuttal: Dict[str, Any],
    memo_summary: str,
    current_price: float,
) -> str:
    bull_md = bull.get("thesis_md", "")
    bear_md = bear.get("independent_bear_md", "")
    bear_attack = bear.get("attack_md", "")
    rebuttal_md = bull_rebuttal.get("rebuttal_md", "")

    return f"""TICKER: {ticker}
CURRENT PRICE: ${current_price}

{sector_prompt_prefix}

LIVING MEMO CONTEXT:
{memo_summary or "(no prior memo)"}

EVIDENCE LEDGER:
{evidence}

BULL CASE:
{bull_md}

BEAR ATTACK ON BULL:
{bear_attack}

INDEPENDENT BEAR CASE:
{bear_md}

BULL REBUTTAL TO BEAR:
{rebuttal_md}

Return JSON:
{{
  "summary": "<one-sentence verdict>",
  "recommendation": "BUY | HOLD | TRIM | AVOID",
  "conviction": "HIGH | MEDIUM | LOW",
  "bull_case": [
    {{"claim": "<headline bull point>", "evidence_refs": ["<tool>"], "confidence": "high|medium|low"}}
  ],
  "bear_case": [
    {{"claim": "<headline bear point>", "evidence_refs": ["<tool>"], "confidence": "high|medium|low"}}
  ],
  "what_would_change_mind": [
    "<specific, monitorable falsifiability condition #1>",
    "<#2>",
    "<#3>"
  ],
  "key_catalysts": [
    {{"event": "<name>", "date": "<YYYY-MM-DD or 'TBD'>", "expected_impact": "<bullish|bearish|mixed> — <why>"}}
  ],
  "target_price_range": {{"low": <number>, "high": <number>, "timeframe": "<e.g. 12 months>"}},
  "trade_plan": {{
    "entry_zone": {{"lower": <number>, "upper": <number>, "logic": "<why this range>"}},
    "stop_methodology": "<volatility|structure|thesis> — <specific level or condition>",
    "stop_price": <number or null>,
    "targets": [
      {{"price": <number>, "size_to_take_off_pct": <number>, "rationale": "<why>"}}
    ],
    "time_stop": "<condition for time-based exit>",
    "position_size_pct": <0-15 — % of deployable capital>,
    "rationale": "<1-2 sentence size justification>"
  }}
}}

Hard requirements:
- bull_case and bear_case must each have 2-4 items
- what_would_change_mind must have at least 3 specific conditions, each monitorable (a number, a date, an event)
- trade_plan.position_size_pct must be between 0 and 15
- If recommendation is AVOID, position_size_pct = 0 and targets may be empty"""


def synthesize(
    ticker: str,
    ledger,                                  # tools.EvidenceLedger
    bull: Dict[str, Any],
    bear: Dict[str, Any],
    bull_rebuttal: Dict[str, Any],
    current_price: float,
    sector_prompt_prefix: str = "",
    memo_summary: str = "",
) -> Dict[str, Any]:
    """Produce the structured verdict."""
    from llm_service import _get_provider_and_model

    evidence = ledger.evidence_prompt(max_chars_per_tool=1200)
    user_prompt = _build_judge_prompt(
        ticker=ticker,
        sector_prompt_prefix=sector_prompt_prefix,
        evidence=evidence,
        bull=bull, bear=bear, bull_rebuttal=bull_rebuttal,
        memo_summary=memo_summary,
        current_price=current_price,
    )

    try:
        provider, model = _get_provider_and_model("thesis", role="judge")
        verdict = provider.complete_json(JUDGE_SYSTEM, user_prompt, model)
    except Exception as e:
        logger.warning(f"Judge failed: {e}")
        return _fallback_verdict(current_price, error=str(e))

    if not isinstance(verdict, dict) or "recommendation" not in verdict:
        logger.warning("Judge returned malformed verdict")
        return _fallback_verdict(current_price, error="malformed verdict")

    # Coerce required fields
    verdict.setdefault("summary", "")
    verdict.setdefault("conviction", "LOW")
    verdict.setdefault("bull_case", [])
    verdict.setdefault("bear_case", [])
    verdict.setdefault("what_would_change_mind", [])
    verdict.setdefault("key_catalysts", [])
    verdict.setdefault("target_price_range", {"low": current_price, "high": current_price, "timeframe": "12 months"})
    verdict.setdefault("trade_plan", {})
    from agents.evidence_validation import validate_claim_refs
    verdict = validate_claim_refs(verdict, ledger, [
        ("bull_case", "claim"),
        ("bear_case", "claim"),
    ])
    # Clamp position size
    tp = verdict.get("trade_plan") or {}
    try:
        size = float(tp.get("position_size_pct", 0) or 0)
    except (TypeError, ValueError):
        size = 0.0
    tp["position_size_pct"] = max(0.0, min(15.0, size))
    verdict["trade_plan"] = tp

    return verdict


def _fallback_verdict(current_price: float, error: str = "") -> Dict[str, Any]:
    """Used when the LLM judge call fails."""
    return {
        "summary": f"Judge unavailable: {error}" if error else "Insufficient evidence for verdict",
        "recommendation": "HOLD",
        "conviction": "LOW",
        "bull_case": [],
        "bear_case": [],
        "what_would_change_mind": ["Configure LLM provider to enable verdict synthesis"],
        "key_catalysts": [],
        "target_price_range": {"low": current_price, "high": current_price, "timeframe": "N/A"},
        "trade_plan": {
            "entry_zone": {"lower": current_price, "upper": current_price, "logic": "no plan generated"},
            "stop_methodology": "n/a",
            "stop_price": None,
            "targets": [],
            "time_stop": "n/a",
            "position_size_pct": 0.0,
            "rationale": "No verdict — do not size",
        },
        "error": error or None,
    }

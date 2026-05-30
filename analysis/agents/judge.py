"""
agents.judge — Verdict agent.

Reads the bull case, bear case, bull rebuttal, and full evidence ledger, then produces the
final structured verdict including falsifiability conditions and a trade plan.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


JUDGE_SYSTEM = """You are a portfolio manager about to allocate real capital for an individual investor.

You receive a bull case, a bear case, a bull rebuttal defending the thesis, and the raw evidence. Your job:
1. Weigh all inputs and produce a recommendation
2. Set conviction honestly — only HIGH when bull thesis is strong AND bear concerns are well-addressed
3. Define WHAT WOULD CHANGE YOUR MIND — falsifiable, monitorable conditions
4. Produce a trade plan: entry zone, stop methodology, targets, time stop, position size guidance
5. Explicitly weigh and debate technical indicators (RSI overbought/oversold, MACD, golden/death cross, moving averages, chart patterns from [technicals]) and relative S&P 500 scanner rankings (sector momentum, forward multiples vs sector/market, beta rankings, spotlight tags from [sp500_lookup]) to synthesize optimal entry/exit levels and portfolio fit.

Conviction calibration:
- HIGH: multiple independent supports; bear case addressed with evidence; falsifiability conditions clear and distant
- MEDIUM: thesis reasonable but at least one bear argument partially unresolved, OR key evidence missing
- LOW: significant unresolved questions; flag for further research not capital deployment

If USER PORTFOLIO CONTEXT is provided, the user already owns this stock — your recommendation MUST be position-aware:
- Recommendation choice: prefer TRIM over AVOID when an existing position has appreciated and the thesis is only partially impaired; reserve AVOID for thesis-broken cases requiring full exit.
- Position sizing: position_size_pct is the TARGET weight after acting, not an incremental add. If current weight already exceeds the target, the implicit action is to trim down; if below, it's to add up.
- Cost-basis sensitivity: if unrealized_pnl_pct is materially positive (>+30%) and the bear case has merit, lean toward TRIM rather than HOLD to crystallize gains.
- Concentration: never recommend pushing a single name above 15% of portfolio regardless of conviction.

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
    portfolio_context: Dict[str, Any] = None,
) -> str:
    bull_md = bull.get("thesis_md", "")
    bear_md = bear.get("independent_bear_md", "")
    bear_attack = bear.get("attack_md", "")
    rebuttal_md = bull_rebuttal.get("rebuttal_md", "")

    pc_block = ""
    if portfolio_context:
        weight = portfolio_context.get('weight_pct')
        cost = portfolio_context.get('avg_cost')
        pnl = portfolio_context.get('unrealized_pnl_pct')
        sector_w = portfolio_context.get('sector_weight_pct')
        total_v = portfolio_context.get('total_value')
        lines = ["USER PORTFOLIO CONTEXT (the user ALREADY OWNS this position):"]
        if weight is not None:
            lines.append(f"- Current weight: {weight:.2f}% of portfolio")
        if cost is not None:
            lines.append(f"- Avg cost basis: ${cost}")
        if pnl is not None:
            lines.append(f"- Unrealized P&L: {pnl:+.2f}% vs cost")
        if sector_w is not None:
            lines.append(f"- Sector concentration: {sector_w}%")
        if total_v is not None:
            lines.append(f"- Total portfolio value: ${total_v}")
        lines.append("")
        lines.append("Position-aware sizing rules:")
        lines.append("- position_size_pct is the TARGET weight after the trade (not an incremental add).")
        lines.append("- If you want to trim: target_weight < current_weight, recommendation TRIM.")
        lines.append("- If you want to add: target_weight > current_weight, recommendation BUY.")
        lines.append("- If thesis intact and weight in band (e.g. 5-12%): HOLD with position_size_pct = current_weight.")
        lines.append("- AVOID/SELL means target weight = 0 (full exit).")
        lines.append("- Hard cap: never set position_size_pct above 15% regardless of conviction.")
        pc_block = "\n".join(lines)

    return f"""TICKER: {ticker}
CURRENT PRICE: ${current_price}

{sector_prompt_prefix}

LIVING MEMO CONTEXT:
{memo_summary or "(no prior memo)"}

{pc_block}

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
    "position_size_pct": <0-15 — % of portfolio>,
    "rationale": "<1-2 sentence size justification>"
  }}
}}

Hard requirements:
- bull_case and bear_case must each have 2-4 items
- what_would_change_mind must have at least 3 specific conditions, each monitorable (a number, a date, an event)
- trade_plan.position_size_pct must be between 0 and 15
- If recommendation is AVOID, position_size_pct = 0 and targets may be empty
- If portfolio context provided, factor concentration into position_size_pct"""


def synthesize(
    ticker: str,
    ledger,                                  # tools.EvidenceLedger
    bull: Dict[str, Any],
    bear: Dict[str, Any],
    bull_rebuttal: Dict[str, Any],
    current_price: float,
    sector_prompt_prefix: str = "",
    memo_summary: str = "",
    portfolio_context: Dict[str, Any] = None,
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
        portfolio_context=portfolio_context,
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

"""
agents.planner — investigation planner.

Given the ticker, current Living Memo, evidence gathered so far, sector profile,
and remaining budget, the planner LLM decides which tool calls to make next.

Output JSON schema:
{
  "next_calls": [
    {"tool": "<tool_name>", "args": {"ticker": "NVDA", ...}, "reason": "..."},
    ...
  ],
  "done": false,
  "summary": "<one-line explanation of plan>"
}
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Hard upper bound on tools per planner round (cost containment)
MAX_CALLS_PER_ROUND = 5
# Hard upper bound on planner iterations per session
MAX_PLANNER_ITERATIONS = 4


PLANNER_SYSTEM = """You are the investigation planner for a financial research agent.
You decide which data-gathering tools to call next to investigate a stock.
You DO NOT make investment recommendations — that comes later.

Guiding principles:
- Prefer tools that fill gaps the existing Living Memo identifies as Open Questions
- Sector matters — different sectors need different tools (the user will tell you which are required)
- Don't repeat tool calls that are already in the evidence ledger
- Respect the budget — pick a small set of high-value calls
- When you have sufficient evidence to support a thesis OR the budget is low, set done=true

Output STRICT JSON only. No prose, no markdown fences."""


def _build_planner_prompt(
    ticker: str,
    memo_open_questions: List[str],
    sector_key: str,
    required_tools: List[str],
    evidence_summary: str,
    budget_snapshot: Dict[str, float],
    prior_plan_done: bool,
    available_tools: List[Dict[str, Any]],
    iteration: int,
    max_iterations: int,
) -> str:
    tool_lines = []
    for t in available_tools:
        tool_lines.append(
            f"  - {t['name']}: {t['description']}"
        )
    tools_block = "\n".join(tool_lines)

    questions_block = (
        "\n".join(f"  - {q}" for q in memo_open_questions[:8])
        if memo_open_questions else "  (memo has no open questions; pick foundational tools first)"
    )

    required_block = ", ".join(required_tools) if required_tools else "(no sector-specific requirements)"

    return f"""TICKER: {ticker}
SECTOR: {sector_key}
SECTOR-REQUIRED TOOLS: {required_block}

LIVING MEMO OPEN QUESTIONS:
{questions_block}

EVIDENCE LEDGER (already gathered):
{evidence_summary if evidence_summary else "  (empty — this is the first round)"}

BUDGET STATUS: ${budget_snapshot['remaining_usd']:.4f} remaining of ${budget_snapshot['max_usd']:.2f}, {budget_snapshot['remaining_sec']:.0f}s wall clock remaining

PLANNER ITERATION: {iteration}/{max_iterations}

AVAILABLE TOOLS:
{tools_block}

Return JSON:
{{
  "next_calls": [
    {{"tool": "<tool_name from the list above>", "args": {{"ticker": "{ticker}"}}, "reason": "<why this tool now>"}}
  ],
  "done": <true if you have sufficient evidence OR budget low OR no useful tools remain; false to keep going>,
  "summary": "<one-line plan summary>"
}}

Pick at most {MAX_CALLS_PER_ROUND} tools this round. If done=true, next_calls may be empty.
If the previous iteration finished gathering most foundational data, prefer specialized tools that address remaining open questions."""


def _validate_plan(
    plan: Dict[str, Any],
    available_tool_names: List[str],
    ticker: str,
) -> Dict[str, Any]:
    """Sanitize the planner's output: drop unknown tools, ensure ticker arg, cap count."""
    out_calls: List[Dict[str, Any]] = []
    raw_calls = plan.get("next_calls", []) or []
    if not isinstance(raw_calls, list):
        raw_calls = []

    seen_signatures: set = set()
    for call in raw_calls[:MAX_CALLS_PER_ROUND * 2]:  # we'll cap after dedup
        if not isinstance(call, dict):
            continue
        tool_name = call.get("tool")
        if tool_name not in available_tool_names:
            logger.debug(f"Planner picked unknown tool '{tool_name}' — dropping")
            continue
        args = call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        # Ensure ticker is present if the tool likely needs it
        args.setdefault("ticker", ticker)
        reason = call.get("reason") or ""
        # Dedupe by tool+args signature
        sig = (tool_name, tuple(sorted(args.items())))
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        out_calls.append({"tool": tool_name, "args": args, "reason": reason})
        if len(out_calls) >= MAX_CALLS_PER_ROUND:
            break

    return {
        "next_calls": out_calls,
        "done": bool(plan.get("done", False)) or len(out_calls) == 0,
        "summary": str(plan.get("summary", ""))[:300],
    }


def plan(
    ticker: str,
    memo_open_questions: List[str],
    sector_key: str,
    required_tools: List[str],
    ledger,                          # tools.EvidenceLedger
    budget,                          # tools.Budget
    iteration: int = 0,
    max_iterations: int = MAX_PLANNER_ITERATIONS,
    prior_plan_done: bool = False,
) -> Dict[str, Any]:
    """Run the planner LLM and return a validated plan."""
    from tools import tools_schema_for_llm, tool_names
    from llm_service import _get_provider_and_model

    available_schemas = tools_schema_for_llm()
    available_names = tool_names()

    # Hard stop: if budget exhausted or iterations exceeded → done
    if budget.exhausted() or iteration >= max_iterations:
        return {
            "next_calls": [],
            "done": True,
            "summary": "Budget/iteration limit reached",
        }

    prompt_user = _build_planner_prompt(
        ticker=ticker,
        memo_open_questions=memo_open_questions,
        sector_key=sector_key,
        required_tools=required_tools,
        evidence_summary=ledger.evidence_prompt(max_chars_per_tool=600),
        budget_snapshot=budget.snapshot(),
        prior_plan_done=prior_plan_done,
        available_tools=available_schemas,
        iteration=iteration,
        max_iterations=max_iterations,
    )

    try:
        provider, model = _get_provider_and_model("analysis")
        raw = provider.complete_json(PLANNER_SYSTEM, prompt_user, model)
    except Exception as e:
        logger.warning(f"Planner LLM failed: {e} — falling back to default plan")
        return _fallback_plan(ticker, ledger, required_tools, available_names)

    if not isinstance(raw, dict) or "next_calls" not in raw:
        logger.warning(f"Planner returned unexpected shape; falling back")
        return _fallback_plan(ticker, ledger, required_tools, available_names)

    return _validate_plan(raw, available_names, ticker)


def _fallback_plan(
    ticker: str,
    ledger,
    required_tools: List[str],
    available_names: List[str],
) -> Dict[str, Any]:
    """When the LLM planner fails, build a deterministic default plan.

    Round 1 (no evidence yet): call core foundational tools.
    Round 2+: try sector-required tools not yet called.
    """
    foundational = ["fundamentals", "financial_trends", "technicals", "sentiment"]
    already_called = {r.tool_name for r in ledger.results}

    if not already_called:
        candidates = [t for t in foundational if t in available_names]
    else:
        # Try sector-required tools next
        candidates = [t for t in required_tools if t in available_names and t not in already_called]
        if not candidates:
            # Try anything foundational we haven't done yet
            candidates = [t for t in foundational if t in available_names and t not in already_called]

    calls = [
        {"tool": t, "args": {"ticker": ticker}, "reason": "fallback plan (planner LLM unavailable)"}
        for t in candidates[:MAX_CALLS_PER_ROUND]
    ]

    return {
        "next_calls": calls,
        "done": len(calls) == 0,
        "summary": f"Fallback plan: {len(calls)} foundational tool(s)",
    }

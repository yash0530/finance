"""
agent_loop.py — v2 deep research orchestrator.

Replaces the fixed 8-stage pipeline with an agentic loop:

  1. Load Living Memo (or empty skeleton)
  2. Classify sector → load sector analyzer
  3. Planner round: pick tools to call
  4. Execute tools (parallelizable; each emits a result with citations)
  5. Re-plan until done / budget / iteration limit hit
  6. Bull agent argues
  7. Bear agent argues + attacks bull
  8. Judge produces structured verdict + trade plan
  9. Self-critique reviews verdict — may trigger an extra planner round
 10. Memo synthesizer proposes Living Memo delta
 11. Persist: report, tool log, recommendation, memo version

Two entry points:
  run_deep_research(...)  — synchronous, returns the full report
  stream_deep_research(...)— generator yielding SSE-formatted strings per step

The SSE event vocabulary is documented in next_gen_tool.md §20.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

from tools import Budget, EvidenceLedger, Tool, get_tool, all_tools

logger = logging.getLogger(__name__)


# ============================================================================
# Budget profiles
# ============================================================================

BUDGET_PROFILES = {
    "quick":  Budget(max_usd=0.10, max_wall_clock_sec=60),
    "normal": Budget(max_usd=0.60, max_wall_clock_sec=180),
    "deep":   Budget(max_usd=2.00, max_wall_clock_sec=420),
}


def make_budget(profile: str = "normal") -> Budget:
    """Return a fresh Budget for the named profile."""
    template = BUDGET_PROFILES.get(profile.lower(), BUDGET_PROFILES["normal"])
    # Return a fresh instance (Budget's started_at would be stale on the template)
    return Budget(max_usd=template.max_usd, max_wall_clock_sec=template.max_wall_clock_sec)


# ============================================================================
# SSE helpers
# ============================================================================

def _sse(event: str, data: Dict[str, Any]) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


# ============================================================================
# Tool execution
# ============================================================================

def _execute_tool_call(call: Dict[str, Any]) -> Tuple[Dict[str, Any], Any]:
    """Execute one planner-emitted tool call. Returns (call, ToolResult)."""
    tool_name = call.get("tool")
    args = call.get("args") or {}
    tool = get_tool(tool_name)
    if not tool:
        from tools import ToolResult
        return call, ToolResult(
            tool_name=tool_name or "<unknown>",
            data={},
            error=f"Tool '{tool_name}' not registered",
            confidence="low",
        )
    try:
        result = tool.execute(**args)
    except Exception as e:
        from tools import ToolResult
        result = ToolResult(
            tool_name=tool_name, data={},
            error=f"Tool {tool_name} raised: {e}", confidence="low",
        )
    return call, result


def _execute_calls_parallel(calls: List[Dict[str, Any]], max_workers: int = 4) -> List[Tuple[Dict[str, Any], Any]]:
    """Execute multiple tool calls in parallel."""
    if not calls:
        return []
    if len(calls) == 1:
        return [_execute_tool_call(calls[0])]

    out = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(calls))) as ex:
        futures = [ex.submit(_execute_tool_call, c) for c in calls]
        for f in as_completed(futures):
            try:
                out.append(f.result())
            except Exception as e:
                logger.exception(f"Tool execution future raised: {e}")
    return out


# ============================================================================
# Memo + sector helpers (lazy import so partial-build still works)
# ============================================================================

def _load_memo(ticker: str) -> Dict:
    try:
        import living_memo
        return living_memo.load_or_empty(ticker)
    except ImportError:
        logger.debug("living_memo not yet available — using empty memo dict")
        return {"content_json": {}, "current_version": 0}


def _classify_sector(ticker: str, fundamentals_data: Optional[Dict] = None) -> Dict:
    try:
        import sector_router
        cls = sector_router.classify(ticker, fundamentals_data)
        analyzer = sector_router.get_analyzer(cls.get("sector_key", "default"))
        return {
            "classification": cls,
            "analyzer": analyzer,
            "sector_key": cls.get("sector_key", "default"),
            "required_tools": list(getattr(analyzer, "required_tools", lambda: [])()),
            "prompt_prefix": getattr(analyzer, "prompt_prefix", lambda: "")(),
            "peer_cohort": list(getattr(analyzer, "peer_cohort", lambda t: [])(ticker)),
        }
    except ImportError:
        logger.debug("sector_router not yet available — defaulting")
        return {
            "classification": {"sector_key": "default", "method": "unavailable"},
            "analyzer": None,
            "sector_key": "default",
            "required_tools": [],
            "prompt_prefix": "",
            "peer_cohort": [],
        }


def _memo_summary_for_prompt(memo: Dict) -> str:
    """Compact rendering of a Living Memo for inclusion in agent prompts."""
    content = memo.get("content_json") or {}
    if not content:
        return ""
    lines = []
    for section, body in content.items():
        if not isinstance(body, dict):
            continue
        md = (body.get("content_md") or "").strip()
        if not md:
            continue
        lines.append(f"## {section.replace('_',' ').title()}\n{md[:500]}")
    return "\n\n".join(lines)


def _memo_open_questions(memo: Dict) -> List[str]:
    try:
        import living_memo
        return living_memo.get_open_questions(memo)
    except Exception:
        # Best-effort: parse from content
        content = memo.get("content_json") or {}
        oq = content.get("open_questions") or {}
        if isinstance(oq, dict):
            md = oq.get("content_md") or ""
            return [line.lstrip("-* ").strip() for line in md.splitlines() if line.strip().startswith(("-", "*"))]
        return []


# ============================================================================
# Main orchestration
# ============================================================================

def stream_deep_research(
    ticker: str,
    portfolio_context: Optional[Dict] = None,
    budget_profile: str = "normal",
    force_refresh: bool = False,
) -> Generator[str, None, None]:
    """Run the v2 agentic research pipeline, streaming SSE events.

    Yields strings in SSE format. The final event is `report_complete`.
    """
    from agents import planner, bull, bear, judge, self_critique
    from db import (
        log_tool_call, save_research_report, save_recommendation, get_llm_settings,
    )

    ticker = ticker.upper().strip()
    report_id = str(uuid.uuid4())
    budget = make_budget(budget_profile)
    ledger = EvidenceLedger(ticker=ticker)

    # ── Pipeline start ──────────────────────────────────────
    yield _sse("pipeline_start", {
        "report_id": report_id,
        "ticker": ticker,
        "budget": budget.snapshot(),
        "started_at": datetime.now().isoformat(),
    })

    # ── Load memo + classify sector ─────────────────────────
    memo = _load_memo(ticker)
    sector_info = _classify_sector(ticker)
    memo_summary = _memo_summary_for_prompt(memo)
    open_qs = _memo_open_questions(memo)

    yield _sse("context_loaded", {
        "sector_key": sector_info["sector_key"],
        "required_tools": sector_info["required_tools"],
        "memo_version": memo.get("current_version", 0),
        "open_questions_count": len(open_qs),
    })

    # ── Planner / executor loop ─────────────────────────────
    prior_done = False
    for iteration in range(planner.MAX_PLANNER_ITERATIONS):
        if budget.exhausted():
            yield _sse("budget_warning", {"reason": "Budget exhausted before iteration", **budget.snapshot()})
            break

        # Plan
        plan = planner.plan(
            ticker=ticker,
            memo_open_questions=open_qs,
            sector_key=sector_info["sector_key"],
            required_tools=sector_info["required_tools"],
            ledger=ledger,
            budget=budget,
            iteration=iteration,
            prior_plan_done=prior_done,
        )
        yield _sse("agent_plan", {
            "iteration": iteration,
            "next_calls": [{"tool": c["tool"], "reason": c.get("reason", "")} for c in plan["next_calls"]],
            "done": plan["done"],
            "summary": plan["summary"],
        })

        if not plan["next_calls"]:
            prior_done = plan["done"]
            if plan["done"]:
                break
            continue

        # Execute calls in parallel
        for call in plan["next_calls"]:
            yield _sse("tool_call_start", {
                "tool": call["tool"], "args": call["args"], "reason": call.get("reason", ""),
            })

        results = _execute_calls_parallel(plan["next_calls"])

        for call, result in results:
            # Charge budget
            budget.charge(result.cost_usd)
            ledger.add(result)

            # Audit log
            try:
                log_tool_call(
                    report_id=report_id,
                    tool_name=result.tool_name,
                    args=call.get("args", {}),
                    result_summary=result.summary(max_chars=600),
                    sources=[s.to_dict() for s in result.sources],
                    confidence=result.confidence,
                    cost_usd=result.cost_usd,
                    latency_ms=result.latency_ms,
                    cached=result.cached,
                    error=result.error,
                )
            except Exception as e:
                logger.warning(f"Tool-log persist failed: {e}")

            if result.is_ok():
                yield _sse("tool_call_complete", {
                    "tool": result.tool_name,
                    "confidence": result.confidence,
                    "cached": result.cached,
                    "latency_ms": result.latency_ms,
                    "data_keys": list(result.data.keys())[:25],
                    "data": result.data,            # full data — UI may render it
                    "sources": [s.to_dict() for s in result.sources],
                })
            else:
                yield _sse("tool_call_error", {
                    "tool": result.tool_name,
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                })

        prior_done = plan["done"]
        if plan["done"]:
            break

    # ── Debate: Bull ───────────────────────────────────────
    yield _sse("debate_start", {"phase": "bull"})
    bull_thesis = bull.argue(
        ticker=ticker, ledger=ledger,
        sector_prompt_prefix=sector_info["prompt_prefix"],
        memo_summary=memo_summary,
    )
    yield _sse("debate_turn", {"agent": "bull", "output": bull_thesis})

    # ── Debate: Bear ───────────────────────────────────────
    yield _sse("debate_start", {"phase": "bear"})
    bear_thesis = bear.argue(
        ticker=ticker, ledger=ledger, bull_thesis=bull_thesis,
        sector_prompt_prefix=sector_info["prompt_prefix"],
        memo_summary=memo_summary,
    )
    yield _sse("debate_turn", {"agent": "bear", "output": bear_thesis})

    # ── Judge ──────────────────────────────────────────────
    yield _sse("debate_start", {"phase": "judge"})
    # Get current price from fundamentals if available; fall back to 0
    fund_result = ledger.latest_by_tool("fundamentals")
    current_price = 0.0
    if fund_result and fund_result.is_ok():
        current_price = float(fund_result.data.get("current_price") or 0)

    verdict = judge.synthesize(
        ticker=ticker, ledger=ledger,
        bull=bull_thesis, bear=bear_thesis,
        current_price=current_price,
        sector_prompt_prefix=sector_info["prompt_prefix"],
        memo_summary=memo_summary,
        portfolio_context=portfolio_context,
    )
    yield _sse("debate_complete", {"verdict": verdict})

    # ── Self-critique ──────────────────────────────────────
    yield _sse("self_critique_start", {})
    critique = self_critique.critique(ticker=ticker, verdict=verdict, ledger=ledger)
    yield _sse("self_critique", critique)

    # ── Memo synthesis (best-effort; module may not exist yet) ──
    memo_delta = None
    try:
        from agents import memo_synth
        memo_delta = memo_synth.synthesize_memo_update(
            ticker=ticker, old_memo=memo.get("content_json", {}),
            evidence_ledger=ledger, verdict=verdict,
        )
        # Persist proposed new memo (auto-accept for now; UI can override later)
        try:
            import living_memo
            new_version = living_memo.save(
                ticker=ticker,
                content_json=memo_delta.get("new_memo", memo.get("content_json", {})),
                delta_summary=memo_delta.get("delta_summary", ""),
                source_report_id=report_id,
                user_edited=False,
            )
            memo_delta["new_version"] = new_version
        except Exception as e:
            logger.warning(f"Failed to persist memo delta: {e}")
            memo_delta["persistence_error"] = str(e)
        yield _sse("memo_delta_proposed", memo_delta)
    except ImportError:
        logger.debug("memo_synth not yet available; skipping memo update")

    # ── Persist recommendation (for calibration) ───────────
    try:
        rec_id = save_recommendation(
            report_id=report_id, ticker=ticker,
            recommendation=verdict.get("recommendation", "HOLD"),
            conviction=verdict.get("conviction", "LOW"),
            price_at_recommendation=current_price,
            target_low=(verdict.get("target_price_range") or {}).get("low"),
            target_high=(verdict.get("target_price_range") or {}).get("high"),
            stop_loss=(verdict.get("trade_plan") or {}).get("stop_price"),
            thesis_summary=verdict.get("summary", ""),
            what_would_change_mind="\n".join(verdict.get("what_would_change_mind", [])),
        )
    except Exception as e:
        logger.warning(f"Failed to persist recommendation: {e}")
        rec_id = None

    # ── Assemble final report and persist ──────────────────
    report = {
        "report_id": report_id,
        "ticker": ticker,
        "generated_at": datetime.now().isoformat(),
        "version": "v2",
        "budget_profile": budget_profile,
        "budget_used": budget.snapshot(),
        "sector": sector_info["classification"],
        "evidence": ledger.to_dict(),
        "bull_thesis": bull_thesis,
        "bear_thesis": bear_thesis,
        "verdict": verdict,
        "self_critique": critique,
        "memo_delta": memo_delta,
        "recommendation_id": rec_id,
        "portfolio_context": portfolio_context,
    }

    try:
        settings = get_llm_settings()
        save_research_report(
            report_id=report_id, ticker=ticker, report=report,
            llm_conversations=[],  # we have tool_call_log + verdict; granular LLM dumps optional
            llm_provider=settings.get("provider", ""),
            llm_model=settings.get("model_deep", ""),
        )
    except Exception as e:
        logger.warning(f"Final report persist failed: {e}")

    yield _sse("report_complete", {
        "report_id": report_id,
        "ticker": ticker,
        "recommendation": verdict.get("recommendation"),
        "conviction": verdict.get("conviction"),
        "evidence_tool_count": len(ledger.results),
        "cost_used_usd": budget.spent_usd,
        "wall_clock_sec": round(time.time() - budget.started_at, 1),
    })


def run_deep_research(
    ticker: str,
    portfolio_context: Optional[Dict] = None,
    budget_profile: str = "normal",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Synchronous version: drains the SSE stream and returns the final report.

    Useful for tests and non-streaming consumers.
    """
    final_report: Dict[str, Any] = {}
    last_complete: Dict[str, Any] = {}

    for raw in stream_deep_research(
        ticker, portfolio_context, budget_profile, force_refresh,
    ):
        # Lightweight SSE parse: we only need to catch report_complete
        if raw.startswith("event: report_complete"):
            # The next line in SSE is "data: <json>\n\n"
            data_line = next(
                (l for l in raw.splitlines() if l.startswith("data: ")),
                "data: {}",
            )
            last_complete = json.loads(data_line[len("data: "):])

    # Re-fetch the persisted report (which contains the verdict, memo delta, etc.)
    if last_complete.get("report_id"):
        try:
            from db import get_research_report
            persisted = get_research_report(last_complete["report_id"])
            if persisted:
                final_report = persisted["report"]
        except Exception as e:
            logger.warning(f"Could not re-fetch persisted report: {e}")
    return final_report or last_complete

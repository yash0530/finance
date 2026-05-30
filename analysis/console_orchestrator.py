"""
console_orchestrator.py — slash-command dispatcher for the Analysis Console.

Parses a command string and returns an SSE generator. All LLM work flows through
agent_loop (Budget-enforced); this module never calls a provider directly.

Commands:
  /thesis <T>          → stream_deep_research(T, budget='normal')   ~$0.60
  /dossier <T>         → stream_deep_research(T, budget='deep')     ~$2-15
  /why <T>             → run_quick_take(T) (single SSE block)       ~$0.05
  /theme <slug>        → per-constituent evidence → bull/bear/judge theme verdict
  /compare <A> <B>...  → parallel quick deep-research → compare_synth ranking
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Generator, List, Tuple

import agent_loop
import db

logger = logging.getLogger(__name__)



def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def parse_command(raw: str) -> Tuple[str, List[str]]:
    parts = (raw or "").strip().split()
    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = [a.upper() for a in parts[1:]]
    return cmd, args


def run(raw: str) -> Generator[str, None, None]:
    """Dispatch a command string to its SSE generator."""
    cmd, args = parse_command(raw)

    yield _sse("console_start", {"command": raw.strip(), "parsed": cmd, "args": args,
                                 "started_at": datetime.now().isoformat()})

    if cmd in ("/thesis", "/dossier"):
        if not args:
            yield _sse("console_error", {"error": f"Usage: {cmd} <TICKER>"})
            return
        yield from _run_research(args[0], "normal" if cmd == "/thesis" else "deep")

    elif cmd == "/why":
        if not args:
            yield _sse("console_error", {"error": "Usage: /why <TICKER>"})
            return
        yield from _run_why(args[0])

    elif cmd == "/theme":
        if not args:
            yield _sse("console_error", {"error": "Usage: /theme <slug>"})
            return
        yield from _run_theme(raw.strip().split()[1])  # preserve original case for slug

    elif cmd == "/compare":
        if len(args) < 2:
            yield _sse("console_error", {"error": "Usage: /compare <A> <B> [<C> ...]"})
            return
        yield from _run_compare(args)

    else:
        yield _sse("console_error", {
            "error": f"Unknown command '{cmd}'. Try /thesis, /dossier, /why, /theme, /compare.",
        })


# ── /thesis, /dossier ────────────────────────────────────────────────────

def _run_research(ticker: str, budget_profile: str) -> Generator[str, None, None]:
    from agent_loop import stream_deep_research
    yield from stream_deep_research(ticker=ticker, budget_profile=budget_profile)


# ── /why ─────────────────────────────────────────────────────────────────

def _run_why(ticker: str) -> Generator[str, None, None]:
    cached = db.get_hypothesis(ticker, max_age_seconds=4 * 3600)
    if cached:
        yield _sse("quick_take", {
            "ticker": ticker, "why_md": cached["content_md"],
            "evidence_refs": cached.get("evidence_refs", []),
            "cost_usd": cached.get("cost_usd"), "cached": True,
        })
        yield _sse("console_complete", {"command": f"/why {ticker}", "cached": True})
        return

    take = agent_loop.run_quick_take(ticker)
    db.save_hypothesis(
        ticker=ticker, content_md=take.get("why_md", ""),
        cost_usd=take.get("cost_usd", 0.0), evidence_refs=take.get("evidence_refs", []),
    )
    yield _sse("quick_take", {**take, "cached": False})
    yield _sse("console_complete", {"command": f"/why {ticker}", "cost_used_usd": take.get("cost_usd", 0.0)})


# ── /theme ───────────────────────────────────────────────────────────────

THEME_TOOLS = ["fundamentals", "news_tape", "technicals"]


def _run_theme(slug: str) -> Generator[str, None, None]:
    import themes_service
    from tools import EvidenceLedger, get_tool
    from agent_loop import make_budget, _execute_calls_parallel
    from agents import bull, bear, judge
    from llm_service import LLMCallSession

    detail = themes_service.get_theme_detail(slug)
    if not detail:
        yield _sse("console_error", {"error": f"Unknown theme '{slug}'"})
        return

    tickers = [t["ticker"] for t in detail.get("tickers", [])]
    if not tickers:
        yield _sse("console_error", {"error": f"Theme '{slug}' has no tickers"})
        return

    yield _sse("theme_start", {"slug": slug, "name": detail["name"], "ticker_count": len(tickers)})

    budget = make_budget("normal")
    ledger = EvidenceLedger(ticker=slug)

    # Gather evidence per constituent (free tools only) in parallel.
    calls = []
    for t in tickers:
        for tool_name in THEME_TOOLS:
            calls.append({"tool": tool_name, "args": {"ticker": t}})
    for call, result in _execute_calls_parallel(calls, max_workers=8):
        budget.charge(result.cost_usd)
        ledger.add(result)
        if result.is_ok():
            yield _sse("tool_call_complete", {
                "tool": result.tool_name, "confidence": result.confidence,
                "latency_ms": result.latency_ms,
                "args": call.get("args", {}),
            })

    theme_prefix = (
        f"THEME-LEVEL ANALYSIS: '{detail['name']}' ({slug}). "
        f"Constituents: {', '.join(tickers)}. "
        f"Argue about the THEME as a whole — secular drivers, which names lead, "
        f"and the strongest risk to the theme thesis."
    )

    session = LLMCallSession(report_id=f"theme-{slug}")
    session.__enter__()
    try:
        yield _sse("debate_start", {"phase": "bull"})
        bull_out = bull.argue(ticker=slug, ledger=ledger, sector_prompt_prefix=theme_prefix)
        yield _sse("debate_turn", {"agent": "bull", "output": bull_out})

        yield _sse("debate_start", {"phase": "bear"})
        bear_out = bear.argue(ticker=slug, ledger=ledger, bull_thesis=bull_out, sector_prompt_prefix=theme_prefix)
        yield _sse("debate_turn", {"agent": "bear", "output": bear_out})

        yield _sse("debate_start", {"phase": "judge"})
        verdict = judge.synthesize(
            ticker=slug, ledger=ledger, bull=bull_out, bear=bear_out,
            bull_rebuttal={}, current_price=0.0, sector_prompt_prefix=theme_prefix,
        )
        yield _sse("debate_complete", {"verdict": verdict})
    finally:
        session.__exit__(None, None, None)

    budget.charge(session.total_cost_usd)
    yield _sse("console_complete", {
        "command": f"/theme {slug}", "ticker_count": len(tickers),
        "cost_used_usd": round(budget.spent_usd, 4),
    })


# ── /compare ─────────────────────────────────────────────────────────────

def _run_compare(tickers: List[str]) -> Generator[str, None, None]:
    from agent_loop import run_deep_research, make_budget
    from agents import compare_synth
    from llm_service import LLMCallSession

    if len(tickers) > 5:
        yield _sse("console_error", {"error": "Budget guard limit: /compare is capped at 5 tickers max to avoid runaway costs."})
        return

    yield _sse("compare_start", {"tickers": tickers})

    def _one(t: str):
        try:
            report = run_deep_research(t, budget_profile="quick")
            return t, report
        except Exception as e:
            logger.warning(f"/compare run for {t} failed: {e}")
            return t, {}

    candidates: List[Dict[str, Any]] = []
    total_candidate_cost = 0.0
    with ThreadPoolExecutor(max_workers=min(4, len(tickers))) as pool:
        for t, report in pool.map(_one, tickers):
            verdict = report.get("verdict") or {}
            cost = report.get("cost_used_usd", 0.0)
            total_candidate_cost += cost

            candidates.append({"ticker": t, "verdict": verdict})
            yield _sse("compare_candidate", {
                "ticker": t,
                "recommendation": verdict.get("recommendation"),
                "conviction": verdict.get("conviction"),
                "summary": (verdict.get("summary") or "")[:400],
            })

    budget = make_budget("normal")
    session = LLMCallSession(report_id="compare")
    session.__enter__()
    try:
        ranking = compare_synth.synthesize(candidates)
    finally:
        session.__exit__(None, None, None)
    budget.charge(session.total_cost_usd)

    yield _sse("compare_ranking", ranking)
    yield _sse("console_complete", {
        "command": f"/compare {' '.join(tickers)}",
        "candidate_count": len(candidates),
        "cost_used_usd": round(budget.spent_usd + total_candidate_cost, 4),
    })

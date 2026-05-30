"""
Tests for console_orchestrator — slash-command parsing and dispatch.

LLM + tools are mocked so commands run offline. SSE output is parsed back into
(event, data) tuples for assertions.
"""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import db
import console_orchestrator as orch


# ── SSE parse helper ──────────────────────────────────────────────────────

def _parse_sse(chunks):
    events = []
    for raw in chunks:
        ev, data = None, None
        for line in raw.splitlines():
            if line.startswith("event: "):
                ev = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if ev:
            events.append((ev, data))
    return events


# ── Parsing ───────────────────────────────────────────────────────────────

def test_parse_command():
    assert orch.parse_command("/thesis nvda") == ("/thesis", ["NVDA"])
    assert orch.parse_command("/compare nvda amd avgo") == ("/compare", ["NVDA", "AMD", "AVGO"])
    assert orch.parse_command("  ") == ("", [])


def test_unknown_command_errors():
    events = _parse_sse(orch.run("/bogus NVDA"))
    kinds = [e for e, _ in events]
    assert "console_start" in kinds
    assert "console_error" in kinds


def test_thesis_requires_ticker():
    events = _parse_sse(orch.run("/thesis"))
    assert any(e == "console_error" for e, _ in events)


def test_compare_requires_two_tickers():
    events = _parse_sse(orch.run("/compare NVDA"))
    assert any(e == "console_error" for e, _ in events)


# ── /why ────────────────────────────────────────────────────────────────

def test_why_dispatches_and_caches(monkeypatch):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM hypotheses_cache")
        conn.commit()
    finally:
        conn.close()

    import agent_loop
    monkeypatch.setattr(agent_loop, "run_quick_take", lambda t: {
        "ticker": t, "why_md": "moving on demand [news_tape]",
        "stance": "bullish", "evidence_refs": ["news_tape"], "cost_usd": 0.05,
    })

    events = _parse_sse(orch.run("/why NVDA"))
    kinds = [e for e, _ in events]
    assert "quick_take" in kinds
    assert "console_complete" in kinds
    qt = next(d for e, d in events if e == "quick_take")
    assert qt["cached"] is False
    # Saved to cache → second run is cached
    events2 = _parse_sse(orch.run("/why NVDA"))
    qt2 = next(d for e, d in events2 if e == "quick_take")
    assert qt2["cached"] is True


# ── /compare ─────────────────────────────────────────────────────────────

def test_compare_dispatches(monkeypatch):
    import agent_loop
    monkeypatch.setattr(agent_loop, "run_deep_research", lambda t, budget_profile="quick": {
        "verdict": {"recommendation": "BUY", "conviction": "MEDIUM",
                    "summary": f"{t} looks fine", "target_price_range": {"low": 1, "high": 2}},
    })
    from agents import compare_synth
    monkeypatch.setattr(compare_synth, "synthesize", lambda candidates: {
        "ranking": [{"rank": i + 1, "ticker": c["ticker"], "reason": "r"} for i, c in enumerate(candidates)],
        "winner": candidates[0]["ticker"], "head_to_head": "x", "summary_md": "y",
    })

    events = _parse_sse(orch.run("/compare NVDA AMD AVGO"))
    kinds = [e for e, _ in events]
    assert "compare_start" in kinds
    assert kinds.count("compare_candidate") == 3
    assert "compare_ranking" in kinds
    ranking = next(d for e, d in events if e == "compare_ranking")
    assert len(ranking["ranking"]) == 3


# ── /theme ───────────────────────────────────────────────────────────────

class _FastInfo:
    def __init__(self, p, pc):
        self.last_price = p
        self.previous_close = pc
        self.last_volume = 1000
        self.market_cap = None


def test_theme_unknown_slug_errors():
    events = _parse_sse(orch.run("/theme does-not-exist"))
    assert any(e == "console_error" for e, _ in events)


def test_theme_dispatches(monkeypatch):
    # Seed a theme
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM theme_tickers")
        conn.execute("DELETE FROM themes")
        conn.commit()
    finally:
        conn.close()
    db.upsert_theme("ai", "AI Infra")
    db.add_theme_ticker("ai", "NVDA")
    db.add_theme_ticker("ai", "AMD")

    # Mock the per-constituent tools to return ok results quickly.
    from tools import ToolResult
    import agent_loop

    def fake_calls(calls, max_workers=8):
        out = []
        for c in calls:
            out.append((c, ToolResult(tool_name=c["tool"], data={"x": 1}, confidence="high")))
        return out

    monkeypatch.setattr(agent_loop, "_execute_calls_parallel", fake_calls)

    from agents import bull, bear, judge
    monkeypatch.setattr(bull, "argue", lambda **kw: {"thesis_md": "bull"})
    monkeypatch.setattr(bear, "argue", lambda **kw: {"attack_md": "bear"})
    monkeypatch.setattr(judge, "synthesize", lambda **kw: {"recommendation": "BUY", "summary": "theme verdict"})

    events = _parse_sse(orch.run("/theme ai"))
    kinds = [e for e, _ in events]
    assert "theme_start" in kinds
    assert "debate_complete" in kinds
    assert "console_complete" in kinds
    verdict = next(d for e, d in events if e == "debate_complete")
    assert verdict["verdict"]["recommendation"] == "BUY"

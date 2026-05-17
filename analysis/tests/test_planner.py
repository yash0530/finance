"""
Tests for analysis/agents/planner.py — focused on the C1 change that ensures
macro_context (always) and peer_compare (when sector is known) get seeded into
the plan even if the planner LLM forgets them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from agents.planner import _seed_macro_and_peers, plan, MAX_CALLS_PER_ROUND


# ── Minimal stand-in for tools.EvidenceLedger ──────────────────────────────
@dataclass
class _StubResult:
    tool_name: str


@dataclass
class _StubLedger:
    results: List[_StubResult] = field(default_factory=list)

    def evidence_prompt(self, max_chars_per_tool: int = 600) -> str:
        return "\n".join(f"[{r.tool_name}]" for r in self.results)


# ── Stand-in for tools.Budget snapshot ─────────────────────────────────────
class _StubBudget:
    def __init__(self, exhausted=False, remaining_usd=2.0, remaining_sec=300.0):
        self._exhausted = exhausted
        self.max_usd = 5.0
        self._remaining_usd = remaining_usd
        self._remaining_sec = remaining_sec

    def exhausted(self):
        return self._exhausted

    def snapshot(self):
        return {
            "max_usd": self.max_usd,
            "spent_usd": 0.0,
            "remaining_usd": self._remaining_usd,
            "remaining_sec": self._remaining_sec,
        }


# ============================================================================
# _seed_macro_and_peers unit tests
# ============================================================================

def test_seeds_macro_context_when_missing():
    plan_obj = {"next_calls": [], "done": True, "summary": "nothing"}
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare", "fundamentals"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    tools = [c["tool"] for c in out["next_calls"]]
    assert "macro_context" in tools
    assert out["done"] is False  # un-done because we added work


def test_seeds_peer_compare_when_sector_known():
    plan_obj = {"next_calls": [], "done": False, "summary": ""}
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    tools = [c["tool"] for c in out["next_calls"]]
    assert "peer_compare" in tools
    peer_call = next(c for c in out["next_calls"] if c["tool"] == "peer_compare")
    assert peer_call["args"]["sector"] == "Technology"
    assert peer_call["args"]["ticker"] == "NVDA"


@pytest.mark.parametrize("sector", ["", "unknown", "Unknown", "other", "Other"])
def test_skips_peer_compare_when_sector_unknown(sector):
    plan_obj = {"next_calls": [], "done": False, "summary": ""}
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", sector, ledger, available, iteration=0)

    tools = [c["tool"] for c in out["next_calls"]]
    assert "peer_compare" not in tools
    # macro_context still gets seeded — it's sector-independent
    assert "macro_context" in tools


def test_no_duplicate_if_already_in_ledger():
    plan_obj = {"next_calls": [], "done": False, "summary": ""}
    ledger = _StubLedger(results=[_StubResult("macro_context"), _StubResult("peer_compare")])
    available = ["macro_context", "peer_compare"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    assert out["next_calls"] == []


def test_no_duplicate_if_already_planned():
    plan_obj = {
        "next_calls": [
            {"tool": "macro_context", "args": {"ticker": "NVDA"}, "reason": "planner picked it"},
        ],
        "done": False,
        "summary": "",
    }
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    macro_calls = [c for c in out["next_calls"] if c["tool"] == "macro_context"]
    assert len(macro_calls) == 1  # not duplicated


def test_skips_seeding_after_iteration_1():
    plan_obj = {"next_calls": [], "done": True, "summary": "late round"}
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare"]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=2)

    assert out["next_calls"] == []
    assert out["done"] is True  # unchanged


def test_respects_max_calls_per_round():
    # Pre-fill plan with MAX_CALLS_PER_ROUND items so seeding has no room
    existing = [
        {"tool": f"tool_{i}", "args": {"ticker": "NVDA"}, "reason": "x"}
        for i in range(MAX_CALLS_PER_ROUND)
    ]
    plan_obj = {"next_calls": list(existing), "done": False, "summary": ""}
    ledger = _StubLedger()
    available = ["macro_context", "peer_compare"] + [f"tool_{i}" for i in range(MAX_CALLS_PER_ROUND)]

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    # Total call count capped
    assert len(out["next_calls"]) == MAX_CALLS_PER_ROUND
    # Seeded ones come first (they're prepended)
    assert out["next_calls"][0]["tool"] == "macro_context"


def test_skips_when_tools_unavailable():
    plan_obj = {"next_calls": [], "done": False, "summary": ""}
    ledger = _StubLedger()
    available = ["fundamentals"]  # neither macro_context nor peer_compare available

    out = _seed_macro_and_peers(plan_obj, "NVDA", "Technology", ledger, available, iteration=0)

    assert out["next_calls"] == []


# ============================================================================
# plan() integration — seeding happens after LLM, on fallback paths too
# ============================================================================

def test_plan_seeds_when_llm_forgets(monkeypatch):
    """If the planner LLM returns a plan without macro_context/peer_compare,
    plan() should still inject them."""

    class _StubProvider:
        def complete_json(self, system, user, model):
            return {
                "next_calls": [
                    {"tool": "fundamentals", "args": {"ticker": "NVDA"}, "reason": "baseline"},
                ],
                "done": False,
                "summary": "LLM forgot macro",
            }

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda task, role="unknown": (_StubProvider(), "fake-model"))

    ledger = _StubLedger()
    budget = _StubBudget()

    out = plan(
        ticker="NVDA",
        memo_open_questions=[],
        sector_key="Technology",
        required_tools=[],
        ledger=ledger,
        budget=budget,
        iteration=0,
    )

    tools = [c["tool"] for c in out["next_calls"]]
    assert "macro_context" in tools
    assert "peer_compare" in tools
    assert "fundamentals" in tools


def test_plan_seeds_on_llm_exception(monkeypatch):
    """If the planner LLM raises, the fallback path should still seed."""

    class _BoomProvider:
        def complete_json(self, system, user, model):
            raise RuntimeError("LLM down")

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda task, role="unknown": (_BoomProvider(), "fake-model"))

    ledger = _StubLedger()
    budget = _StubBudget()

    out = plan(
        ticker="NVDA",
        memo_open_questions=[],
        sector_key="Technology",
        required_tools=[],
        ledger=ledger,
        budget=budget,
        iteration=0,
    )

    tools = [c["tool"] for c in out["next_calls"]]
    assert "macro_context" in tools
    assert "peer_compare" in tools


def test_plan_seeds_on_malformed_llm(monkeypatch):
    """If the planner LLM returns junk, the fallback path should still seed."""

    class _JunkProvider:
        def complete_json(self, system, user, model):
            return "not a dict"  # malformed

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda task, role="unknown": (_JunkProvider(), "fake-model"))

    ledger = _StubLedger()
    budget = _StubBudget()

    out = plan(
        ticker="NVDA",
        memo_open_questions=[],
        sector_key="Technology",
        required_tools=[],
        ledger=ledger,
        budget=budget,
        iteration=0,
    )

    tools = [c["tool"] for c in out["next_calls"]]
    assert "macro_context" in tools
    assert "peer_compare" in tools


def test_plan_budget_exhausted_short_circuits(monkeypatch):
    """When the budget is exhausted, plan() returns done=True without seeding —
    we shouldn't add work after the budget's gone."""

    # No LLM should be called — but stub it anyway in case it is
    class _ShouldNotBeCalled:
        def complete_json(self, *a, **kw):
            raise AssertionError("LLM called despite exhausted budget")

    monkeypatch.setattr("llm_service._get_provider_and_model", lambda task, role="unknown": (_ShouldNotBeCalled(), "x"))

    ledger = _StubLedger()
    budget = _StubBudget(exhausted=True)

    out = plan(
        ticker="NVDA",
        memo_open_questions=[],
        sector_key="Technology",
        required_tools=[],
        ledger=ledger,
        budget=budget,
        iteration=0,
    )

    assert out["done"] is True
    assert out["next_calls"] == []

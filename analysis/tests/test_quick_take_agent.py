"""
Unit tests for agents.quick_take — the cheap /why path.

The LLM provider is mocked at llm_service._get_provider_and_model so no network
or API key is required.
"""
from __future__ import annotations

import pytest

import db
from tools import EvidenceLedger, ToolResult, Source


@pytest.fixture(autouse=True)
def _wipe():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM hypotheses_cache")
        conn.commit()
    finally:
        conn.close()
    yield


def _ledger_with_evidence():
    led = EvidenceLedger(ticker="NVDA")
    led.add(ToolResult(
        tool_name="news_tape",
        data={"items": [{"headline": "NVDA ships new GPU"}]},
        sources=[Source(tool="news_tape", field="items", fetched_at="now")],
        confidence="medium",
    ))
    led.add(ToolResult(
        tool_name="technicals",
        data={"rsi": 62.0},
        sources=[Source(tool="technicals", field="rsi", fetched_at="now")],
        confidence="high",
    ))
    return led


class _FakeProvider:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete_json(self, system, user, model):
        self.calls.append((system, user))
        return dict(self._response)


def _patch_provider(monkeypatch, response):
    import llm_service
    fake = _FakeProvider(response)
    monkeypatch.setattr(llm_service, "_get_provider_and_model", lambda task, role="unknown": (fake, "fake-model"))
    return fake


def test_quick_take_returns_structured_why(monkeypatch):
    fake = _patch_provider(monkeypatch, {
        "why_md": "Up on demand [news_tape]. RSI elevated [technicals]. Watch earnings.",
        "stance": "bullish",
        "evidence_refs": ["news_tape", "technicals"],
    })
    from agents import quick_take
    out = quick_take.generate("NVDA", _ledger_with_evidence())
    assert out["stance"] == "bullish"
    assert "[news_tape]" in out["why_md"]
    assert out["error"] is None if "error" in out else True
    assert fake.calls, "LLM should have been called"
    # The evidence prompt should have been passed to the model
    assert "news_tape" in fake.calls[0][1]


def test_quick_take_fills_defaults_on_partial_response(monkeypatch):
    _patch_provider(monkeypatch, {"why_md": "only this"})
    from agents import quick_take
    out = quick_take.generate("NVDA", _ledger_with_evidence())
    assert out["why_md"] == "only this"
    assert out["stance"] == "neutral"
    assert out["evidence_refs"] == []


def test_quick_take_degrades_on_llm_error(monkeypatch):
    import llm_service

    def boom(task, role="unknown"):
        raise RuntimeError("no provider configured")

    monkeypatch.setattr(llm_service, "_get_provider_and_model", boom)
    from agents import quick_take
    out = quick_take.generate("NVDA", _ledger_with_evidence())
    assert out["error"]
    assert out["stance"] == "neutral"
    assert "unavailable" in out["why_md"].lower()

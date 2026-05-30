"""
Unit tests for agents.compare_synth — cross-ticker ranking synthesizer.

The LLM provider is mocked at llm_service._get_provider_and_model.
"""
from __future__ import annotations

import pytest


def _candidates():
    return [
        {"ticker": "NVDA", "verdict": {"recommendation": "BUY", "conviction": "HIGH", "summary": "leader"}},
        {"ticker": "AMD", "verdict": {"recommendation": "HOLD", "conviction": "MEDIUM", "summary": "second"}},
        {"ticker": "AVGO", "verdict": {"recommendation": "BUY", "conviction": "MEDIUM", "summary": "diversified"}},
    ]


class _FakeProvider:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete_json(self, system, user, model):
        self.calls.append((system, user))
        return dict(self._response)


def _patch(monkeypatch, response):
    import llm_service
    fake = _FakeProvider(response)
    monkeypatch.setattr(llm_service, "_get_provider_and_model", lambda task, role="unknown": (fake, "fake-model"))
    return fake


def test_compare_synth_produces_ranking(monkeypatch):
    fake = _patch(monkeypatch, {
        "ranking": [
            {"rank": 1, "ticker": "NVDA", "reason": "highest conviction"},
            {"rank": 2, "ticker": "AVGO", "reason": "diversified"},
            {"rank": 3, "ticker": "AMD", "reason": "only a hold"},
        ],
        "head_to_head": "NVDA vs AVGO on growth",
        "winner": "NVDA",
        "summary_md": "NVDA leads.",
    })
    from agents import compare_synth
    out = compare_synth.synthesize(_candidates())
    assert out["winner"] == "NVDA"
    assert len(out["ranking"]) == 3
    assert out["ranking"][0]["ticker"] == "NVDA"
    # All three tickers should appear in the prompt.
    assert "NVDA" in fake.calls[0][1] and "AMD" in fake.calls[0][1]


def test_compare_synth_no_verdicts():
    from agents import compare_synth
    out = compare_synth.synthesize([{"ticker": "NVDA", "verdict": {}}])
    assert out["error"] == "no_verdicts"
    assert out["ranking"] == []


def test_compare_synth_degrades_on_llm_error(monkeypatch):
    import llm_service

    def boom(task, role="unknown"):
        raise RuntimeError("no provider")

    monkeypatch.setattr(llm_service, "_get_provider_and_model", boom)
    from agents import compare_synth
    out = compare_synth.synthesize(_candidates())
    assert out["error"]
    # Falls back to a naive ranking that still lists every candidate.
    assert len(out["ranking"]) == 3
    assert out["winner"] == "NVDA"

"""
Tests for the Tool foundation: ToolResult, Source, Budget, EvidenceLedger,
and the registry. Tools are exercised with a synthetic ExampleTool.
"""
import time
import pytest

import tools as tool_pkg
from tools import (
    Budget, EvidenceLedger, Source, Tool, ToolResult,
    all_tools, get_tool, register, tools_schema_for_llm,
)


class ExampleTool(Tool):
    name = "example_test_tool"
    description = "Test tool that echoes its args"

    def schema(self):
        return {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        }

    def estimate_cost(self, **args):
        return 0.001

    def _execute(self, ticker, **kwargs):
        return ToolResult(
            tool_name=self.name,
            data={"ticker": ticker, "value": 42},
            sources=[Source(
                tool=self.name, field="value", fetched_at="2026-05-17T00:00:00",
                url="https://example.com", note="synthetic"
            )],
            confidence="high",
            cost_usd=0.001,
        )


class FailingTool(Tool):
    name = "example_failing_tool"
    description = "Always raises"

    def schema(self):
        return {"type": "object", "properties": {}, "required": []}

    def estimate_cost(self, **args):
        return 0.0

    def _execute(self, **args):
        raise RuntimeError("intentional failure")


@pytest.fixture
def ledger():
    return EvidenceLedger(ticker="NVDA")


# ── ToolResult / Source ─────────────────────────────────────────────────

def test_source_to_dict_and_display():
    s = Source(
        tool="fundamentals", field="market_cap",
        fetched_at="2026-05-17T12:00:00", url="https://yf.com",
    )
    d = s.to_dict()
    assert d["tool"] == "fundamentals"
    assert d["url"] == "https://yf.com"
    assert "fundamentals:market_cap" in s.display()


def test_tool_result_basic():
    r = ToolResult(
        tool_name="x", data={"a": 1},
        sources=[Source("x", "a", "2026-05-17T00:00:00")],
    )
    assert r.is_ok()
    assert r.tool_name == "x"
    assert "a: 1" in r.summary() or '"a": 1' in r.summary()


def test_tool_result_error_state():
    r = ToolResult(tool_name="x", data={}, error="something broke")
    assert not r.is_ok()
    assert "ERROR" in r.summary()


# ── Tool execution wrapper ──────────────────────────────────────────────

def test_tool_execute_happy_path():
    t = ExampleTool()
    result = t.execute(ticker="NVDA")
    assert result.is_ok()
    assert result.data["ticker"] == "NVDA"
    assert result.data["value"] == 42
    assert result.tool_name == "example_test_tool"
    assert result.latency_ms >= 0
    assert result.args == {"ticker": "NVDA"}
    assert result.sources[0].url == "https://example.com"


def test_tool_execute_catches_exceptions():
    t = FailingTool()
    result = t.execute()
    assert not result.is_ok()
    assert "intentional failure" in result.error
    assert result.tool_name == "example_failing_tool"


def test_tool_subclass_must_return_toolresult():
    class BadTool(Tool):
        name = "bad"
        description = "returns dict instead of ToolResult"

        def schema(self):
            return {}

        def estimate_cost(self, **args):
            return 0.0

        def _execute(self, **args):
            return {"oops": "not a ToolResult"}

    result = BadTool().execute()
    # The wrapper should convert the TypeError into a clean error result
    assert not result.is_ok()
    assert "ToolResult" in result.error


# ── Budget ──────────────────────────────────────────────────────────────

def test_budget_charge_and_remaining():
    b = Budget(max_usd=1.0, max_wall_clock_sec=60)
    assert b.remaining_usd() == 1.0
    assert not b.exhausted()
    assert b.can_afford(0.5)
    b.charge(0.5)
    assert b.remaining_usd() == 0.5
    b.charge(0.6)  # overdraft is allowed but caps remaining at 0
    assert b.remaining_usd() == 0.0
    assert b.exhausted()


def test_budget_time_exhaustion():
    b = Budget(max_usd=10.0, max_wall_clock_sec=0.01)
    time.sleep(0.05)
    assert b.remaining_sec() == 0.0
    assert b.exhausted()
    assert not b.can_afford(0.001)


def test_budget_snapshot_has_required_keys():
    b = Budget(max_usd=1.5, max_wall_clock_sec=120)
    b.charge(0.3)
    snap = b.snapshot()
    assert {"max_usd", "spent_usd", "remaining_usd", "remaining_sec"} <= snap.keys()


# ── EvidenceLedger ──────────────────────────────────────────────────────

def test_ledger_add_and_lookup(ledger):
    t = ExampleTool()
    ledger.add(t.execute(ticker="NVDA"))
    assert ledger.successful_count() == 1
    assert ledger.failed_count() == 0
    assert ledger.has_tool("example_test_tool")
    assert ledger.latest_by_tool("example_test_tool").data["value"] == 42


def test_ledger_total_cost(ledger):
    ledger.add(ExampleTool().execute(ticker="NVDA"))
    ledger.add(ExampleTool().execute(ticker="AMD"))
    assert ledger.total_cost() == pytest.approx(0.002)


def test_ledger_evidence_prompt_truncates(ledger):
    t = ExampleTool()
    big_data = "x" * 5000
    r = t.execute(ticker="NVDA")
    r.data["bigfield"] = big_data
    ledger.add(r)
    prompt = ledger.evidence_prompt(max_chars_per_tool=500)
    # Should truncate to roughly the requested limit
    assert "[truncated]" in prompt
    assert len(prompt) < 2000


def test_ledger_failure_summary(ledger):
    ledger.add(FailingTool().execute())
    ledger.add(ExampleTool().execute(ticker="NVDA"))
    assert ledger.failed_count() == 1
    assert ledger.successful_count() == 1


def test_ledger_to_dict_is_serializable(ledger):
    import json
    ledger.add(ExampleTool().execute(ticker="NVDA"))
    d = ledger.to_dict()
    # Round-trip JSON to confirm serializability
    s = json.dumps(d, default=str)
    assert "NVDA" in s
    assert d["ticker"] == "NVDA"
    assert d["successful"] == 1


# ── Registry ────────────────────────────────────────────────────────────

def test_register_and_get():
    t = ExampleTool()
    register(t)
    assert get_tool("example_test_tool") is t
    assert "example_test_tool" in all_tools()


def test_register_requires_name():
    class NamelessTool(Tool):
        description = "no name"

        def schema(self):
            return {}

        def estimate_cost(self, **args):
            return 0.0

        def _execute(self, **args):
            return ToolResult(tool_name="", data={})

    with pytest.raises(ValueError):
        register(NamelessTool())


def test_tools_schema_for_llm_shape():
    register(ExampleTool())
    schema = tools_schema_for_llm()
    assert isinstance(schema, list)
    entry = next(s for s in schema if s["name"] == "example_test_tool")
    assert entry["description"] == "Test tool that echoes its args"
    assert "input_schema" in entry

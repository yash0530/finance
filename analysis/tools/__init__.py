"""
analysis.tools — v2 Tool registry.

Every data fetch or computation is a Tool with:
  - schema: JSON-schema describing args (for LLM tool-use)
  - estimate_cost: USD estimate before execution (for budget planning)
  - execute: returns a ToolResult with citation-tagged data

The Agent Loop (analysis/agent_loop.py) uses the registry to plan, execute,
and aggregate evidence. The LLM never fetches data directly — it asks tools.

Importing this module triggers tool registration via the auto-load list at
the bottom. To add a new tool: create analysis/tools/<name>.py implementing
Tool, then add its module to _AUTOLOAD.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

Confidence = Literal["high", "medium", "low"]


# ============================================================================
# Citation + result primitives
# ============================================================================

@dataclass
class Source:
    """A pointer back to where a piece of evidence came from."""
    tool: str                       # tool name that produced this
    field: str                      # which field within the tool's output
    fetched_at: str                 # ISO timestamp
    url: Optional[str] = None       # external URL if applicable (filing, news, transcript)
    note: Optional[str] = None      # human-readable extra context

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def display(self) -> str:
        bits = [f"{self.tool}:{self.field}"]
        if self.url:
            bits.append(self.url)
        return " · ".join(bits)


@dataclass
class ToolResult:
    """The standard return type for every tool."""
    tool_name: str
    data: Dict[str, Any]
    sources: List[Source] = field(default_factory=list)
    confidence: Confidence = "medium"
    cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    error: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    produced_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_ok(self) -> bool:
        return self.error is None and bool(self.data)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["sources"] = [s.to_dict() for s in self.sources]
        return d

    def summary(self, max_chars: int = 800) -> str:
        """One-line / short-block summary suitable for the LLM evidence prompt."""
        if self.error:
            return f"[{self.tool_name}] ERROR: {self.error}"
        try:
            blob = json.dumps(self.data, default=str, ensure_ascii=False)
        except Exception:
            blob = str(self.data)
        if len(blob) > max_chars:
            blob = blob[:max_chars] + "...[truncated]"
        return f"[{self.tool_name} confidence={self.confidence}] {blob}"


# ============================================================================
# Budget
# ============================================================================

@dataclass
class Budget:
    """Wall-clock + dollar budget for a single research session."""
    max_usd: float
    max_wall_clock_sec: float = 300.0
    spent_usd: float = 0.0
    started_at: float = field(default_factory=time.time)

    def remaining_usd(self) -> float:
        return max(0.0, self.max_usd - self.spent_usd)

    def remaining_sec(self) -> float:
        return max(0.0, self.max_wall_clock_sec - (time.time() - self.started_at))

    def exhausted(self) -> bool:
        return self.remaining_usd() <= 0 or self.remaining_sec() <= 0

    def can_afford(self, estimated_cost_usd: float) -> bool:
        return estimated_cost_usd <= self.remaining_usd() and self.remaining_sec() > 0

    def charge(self, amount_usd: float) -> None:
        self.spent_usd += max(0.0, amount_usd)

    def snapshot(self) -> Dict[str, float]:
        return {
            "max_usd": self.max_usd,
            "spent_usd": round(self.spent_usd, 4),
            "remaining_usd": round(self.remaining_usd(), 4),
            "remaining_sec": round(self.remaining_sec(), 1),
        }


# ============================================================================
# Tool base class
# ============================================================================

class Tool(ABC):
    """Base class for all research tools.

    Subclasses must set `name`, `description`, and implement `schema`,
    `estimate_cost`, and `_execute`. The public `execute` wraps timing and
    error handling.
    """
    name: str = ""
    description: str = ""
    # Defaults; subclasses may override
    cache_ttl_seconds: int = 0     # 0 disables built-in caching for this tool
    requires_llm: bool = False     # True if tool internally calls the LLM

    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """Return JSON Schema for arguments. At minimum: {"ticker": "string"}."""
        ...

    @abstractmethod
    def estimate_cost(self, **args) -> float:
        """USD cost estimate (used by planner to budget calls)."""
        ...

    @abstractmethod
    def _execute(self, **args) -> ToolResult:
        """Tool-specific implementation."""
        ...

    # ── Public entry point ─────────────────────────────────────
    def execute(self, **args) -> ToolResult:
        start = time.time()
        try:
            result = self._execute(**args)
            if not isinstance(result, ToolResult):
                raise TypeError(
                    f"Tool {self.name}._execute must return ToolResult; got {type(result)}"
                )
            result.tool_name = result.tool_name or self.name
            result.args = result.args or args
            result.latency_ms = int((time.time() - start) * 1000)
            return result
        except Exception as e:
            logger.exception(f"Tool '{self.name}' failed with args={args}")
            return ToolResult(
                tool_name=self.name,
                data={},
                error=f"{type(e).__name__}: {e}",
                latency_ms=int((time.time() - start) * 1000),
                args=args,
            )


# ============================================================================
# Evidence ledger
# ============================================================================

@dataclass
class EvidenceLedger:
    """In-memory evidence store for a single research session.

    Tools deposit ToolResults here; agents (bull/bear/judge) read from here.
    """
    ticker: str
    results: List[ToolResult] = field(default_factory=list)

    def add(self, result: ToolResult) -> None:
        self.results.append(result)

    def add_all(self, results: List[ToolResult]) -> None:
        for r in results:
            self.add(r)

    def by_tool(self, name: str) -> List[ToolResult]:
        return [r for r in self.results if r.tool_name == name]

    def latest_by_tool(self, name: str) -> Optional[ToolResult]:
        items = self.by_tool(name)
        return items[-1] if items else None

    def has_tool(self, name: str) -> bool:
        return any(r.tool_name == name and r.is_ok() for r in self.results)

    def all_sources(self) -> List[Source]:
        out: List[Source] = []
        for r in self.results:
            out.extend(r.sources)
        return out

    def total_cost(self) -> float:
        return round(sum(r.cost_usd for r in self.results), 4)

    def successful_count(self) -> int:
        return sum(1 for r in self.results if r.is_ok())

    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.is_ok())

    def evidence_prompt(self, max_chars_per_tool: int = 1200) -> str:
        """Format the entire ledger for an LLM prompt.

        Used by bull/bear/judge agents — they reason only over this string.
        """
        sections: List[str] = []
        # Group by tool, latest first
        seen: set = set()
        for r in reversed(self.results):
            key = r.tool_name
            if key in seen:
                continue
            seen.add(key)
            sections.append(r.summary(max_chars=max_chars_per_tool))
        return "\n\n".join(reversed(sections))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "tool_count": len(self.results),
            "successful": self.successful_count(),
            "failed": self.failed_count(),
            "total_cost_usd": self.total_cost(),
            "results": [r.to_dict() for r in self.results],
        }


# ============================================================================
# Tool registry
# ============================================================================

_REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> None:
    """Register a tool in the global registry."""
    if not tool.name:
        raise ValueError(f"Tool {type(tool).__name__} must have a name")
    if tool.name in _REGISTRY:
        logger.debug(f"Tool '{tool.name}' re-registered (overwriting)")
    _REGISTRY[tool.name] = tool


def get_tool(name: str) -> Optional[Tool]:
    return _REGISTRY.get(name)


def all_tools() -> Dict[str, Tool]:
    return dict(_REGISTRY)


def tool_names() -> List[str]:
    return sorted(_REGISTRY.keys())


def tools_schema_for_llm() -> List[Dict[str, Any]]:
    """Return tool descriptions in a format suitable for the LLM planner."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.schema(),
        }
        for t in _REGISTRY.values()
    ]


# ============================================================================
# Auto-loading concrete tools
# ============================================================================
# Each entry must be a module under analysis/tools/ that calls register()
# at import time. New tools are added here in the order they should appear
# to the planner.
_AUTOLOAD = [
    "fundamentals",
    "financial_trends",
    "technicals",
    "dcf_valuation",
    "sentiment",
    "edgar_filings",
    "qoe_forensics",
    "macro_context",
    "insider_form4",
    "institutional_13f",
    "options_flow",
    "transcripts",
    "catalyst_lookup",
    "peer_compare",
    "alt_data",
    "correlation_analysis",
    "memo_read",
    "calibration_lookup",
]


def _autoload() -> None:
    """Import each tool module so it registers itself."""
    import importlib
    for mod in _AUTOLOAD:
        try:
            importlib.import_module(f"tools.{mod}")
        except ImportError as e:
            # Modules not yet built — silently skip during incremental rollout
            logger.debug(f"Tool module 'tools.{mod}' not available yet: {e}")
        except Exception as e:
            logger.warning(f"Failed to autoload tools.{mod}: {e}")


_autoload()

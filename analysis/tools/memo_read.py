"""
tools.memo_read — read the current Living Memo for a ticker.

Exposed to the planner as a zero-cost meta-tool. The planner uses the memo's
Open Questions + Risk Register to seed each new investigation rather than
re-investigating from scratch.
"""

from datetime import datetime
from typing import Any, Dict

from tools import Source, Tool, ToolResult, register
import living_memo


class MemoReadTool(Tool):
    name = "memo_read"
    description = (
        "Read the current Living Memo for a ticker. Returns the 10-section "
        "knowledge document (identity, moat, long_term_thesis, current_state, "
        "management_track_record, risk_register, open_questions, "
        "recent_observations, past_verdicts, anti_thesis) or {exists: False} "
        "if no memo has been written yet."
    )
    cache_ttl_seconds = 0  # always fresh — the memo is the source of truth
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol (e.g. NVDA)",
                },
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = (ticker or "").upper().strip()
        memo = living_memo.load(ticker)
        if not memo:
            return ToolResult(
                tool_name=self.name,
                data={"exists": False, "ticker": ticker, "sections": {}},
                confidence="low",
            )

        sections = memo.get("content_json") or {}
        version = memo.get("current_version", 1)
        return ToolResult(
            tool_name=self.name,
            data={
                "exists": True,
                "ticker": ticker,
                "version": version,
                "updated_at": memo.get("updated_at", ""),
                "sections": sections,
            },
            sources=[
                Source(
                    tool=self.name,
                    field="memo",
                    fetched_at=datetime.now().isoformat(),
                    note=f"v{version}",
                )
            ],
            confidence="high",
        )


register(MemoReadTool())

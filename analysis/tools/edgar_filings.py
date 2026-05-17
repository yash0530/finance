"""
tools.edgar_filings — wraps edgar_service.summarize_filing as a v2 Tool.

Fetches the most recent 10-K (or 10-Q fallback) from SEC EDGAR, extracts the
Business / Risk Factors / MD&A sections, and LLM-summarizes each. Cached for
24h (filings rarely change).
"""

from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


class EdgarFilingsTool(Tool):
    name = "edgar_filings"
    description = (
        "SEC EDGAR 10-K/10-Q section summaries for a US-listed ticker: "
        "Business, Risk Factors, MD&A — each LLM-summarized into a short "
        "bullet list. Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
    requires_llm = True

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "form_type": {
                    "type": "string",
                    "description": "SEC form type (10-K or 10-Q). Defaults to 10-K.",
                    "enum": ["10-K", "10-Q"],
                },
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        # Three LLM summarizations (business / risks / mda), each ~mid-sized.
        return 0.05

    def _execute(self, ticker: str, form_type: str = "10-K", **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        form_type = (form_type or "10-K").strip()
        cache_key = f"{ticker}:{form_type}"

        cached = get_tool_cache(self.name, cache_key, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached, cached=True),
                confidence="high" if cached.get("available") else "low",
                cached=True,
            )

        from edgar_service import summarize_filing
        try:
            data = summarize_filing(ticker, form_type)
        except Exception as e:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"{type(e).__name__}: {e}", confidence="low",
            )

        if not isinstance(data, dict) or not data:
            return ToolResult(
                tool_name=self.name, data={},
                error="No filing data returned", confidence="low",
            )

        if data.get("error") and not data.get("available"):
            return ToolResult(
                tool_name=self.name, data={},
                error=data["error"], confidence="low",
            )

        save_tool_cache(self.name, cache_key, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence="high" if data.get("available") else "low",
            cost_usd=self.estimate_cost(),
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    note_suffix = " (cached)" if cached else ""

    # Prefer an actual filing URL if present in the result; otherwise
    # link to the company's EDGAR landing page.
    filing_url = (
        data.get("filing_url")
        or data.get("document_url")
        or data.get("index_url")
        or f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={data.get('form_type', '10-K')}"
    )

    sources: List[Source] = []
    section_map = {
        "business": "Business (Item 1)",
        "risks": "Risk Factors (Item 1A)",
        "mda": "MD&A (Item 7)",
    }
    filing_date = data.get("filing_date", "")
    form_type = data.get("form_type", "10-K")

    for key, label in section_map.items():
        if data.get(key):
            sources.append(Source(
                tool="edgar_filings",
                field=key,
                fetched_at=now,
                url=filing_url,
                note=f"SEC {form_type} {filing_date} — {label}{note_suffix}",
            ))

    return sources


register(EdgarFilingsTool())

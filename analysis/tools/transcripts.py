"""
tools.transcripts — Earnings call transcripts via Financial Modeling Prep.

Free, reliable transcripts are scarce. We try the FMP free-tier endpoint and
gracefully degrade if no API key is set. We do NOT call any LLM here — that's
the planner's job. We just fetch + cache.

Pulls last 4 quarters of transcripts, truncates each to 30k chars, and
persists full text to transcripts_cache.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from tools import Source, Tool, ToolResult, register
from db import get_connection, get_tool_cache, save_tool_cache

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3/earning_call_transcript"
TRANSCRIPT_TRUNC = 30_000
FMP_TIMEOUT_SEC = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_n_quarters(n: int = 4) -> List[tuple]:
    """Return [(year, quarter), ...] for the last n quarters, newest first."""
    today = datetime.now()
    q = ((today.month - 1) // 3) + 1
    y = today.year
    out: List[tuple] = []
    for _ in range(n):
        out.append((y, q))
        q -= 1
        if q == 0:
            q = 4
            y -= 1
    return out


def _fmp_get(ticker: str, year: int, quarter: int, api_key: str) -> Optional[str]:
    url = f"{FMP_BASE}/{ticker}?quarter={quarter}&year={year}&apikey={api_key}"
    try:
        resp = requests.get(url, timeout=FMP_TIMEOUT_SEC)
    except Exception as e:
        logger.warning(f"FMP transcript request failed for {ticker} {year}Q{quarter}: {e}")
        return None
    if resp.status_code >= 400:
        logger.info(f"FMP {ticker} {year}Q{quarter} -> {resp.status_code}")
        return None
    try:
        body = resp.json()
    except Exception:
        return None
    if not body:
        return None
    if isinstance(body, list) and body:
        entry = body[0]
        if isinstance(entry, dict):
            return entry.get("content") or entry.get("transcript") or ""
    if isinstance(body, dict):
        return body.get("content") or body.get("transcript") or ""
    return None


def _persist_transcript(ticker: str, quarter: str, text: str) -> None:
    if not text:
        return
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO transcripts_cache
               (ticker, quarter, transcript_text, source, fetched_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(ticker, quarter) DO UPDATE SET
                 transcript_text = excluded.transcript_text,
                 source = excluded.source,
                 fetched_at = excluded.fetched_at""",
            (ticker, quarter, text, "fmp", datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class TranscriptsTool(Tool):
    name = "transcripts"
    description = (
        "Earnings call transcripts (last 4 quarters) for a US-listed ticker via "
        "Financial Modeling Prep. Requires FMP_API_KEY env var; degrades "
        "gracefully if unset. Persists full text to transcripts_cache. "
        "Truncates each transcript to 30k chars in tool output. Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "quarters": {"type": "integer", "default": 4, "description": "How many quarters back to fetch."},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, quarters: int = 4, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        now_iso = datetime.now().isoformat()

        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached.get("quarters_fetched", []), cached=True),
                confidence="high" if cached.get("available") else "low",
                cached=True,
            )

        api_key = os.environ.get("FMP_API_KEY", "").strip()
        if not api_key:
            data = {
                "ticker": ticker,
                "quarters_fetched": [],
                "transcripts": {},
                "available": False,
                "warnings": ["FMP_API_KEY not set — transcripts unavailable"],
                "fetched_at": now_iso,
            }
            # Don't cache permanently — user may add the key shortly. Still
            # cache for the TTL window to avoid retry storms.
            save_tool_cache(self.name, ticker, data)
            return ToolResult(
                tool_name=self.name,
                data=data,
                sources=[],
                confidence="low",
            )

        warnings: List[str] = []
        transcripts: Dict[str, str] = {}
        quarters_fetched: List[str] = []
        sources: List[Source] = []

        for (y, q) in _last_n_quarters(max(1, quarters)):
            label = f"{y}Q{q}"
            text = _fmp_get(ticker, y, q, api_key)
            if not text:
                warnings.append(f"No transcript for {label}")
                continue
            # Persist full text
            try:
                _persist_transcript(ticker, label, text)
            except Exception as e:
                logger.warning(f"Persist transcript {ticker} {label}: {e}")
            # Truncate for tool output
            transcripts[label] = text[:TRANSCRIPT_TRUNC] + (
                "...[truncated]" if len(text) > TRANSCRIPT_TRUNC else ""
            )
            quarters_fetched.append(label)
            sources.append(Source(
                tool="transcripts",
                field=f"transcripts:{label}",
                fetched_at=now_iso,
                url=f"{FMP_BASE}/{ticker}?quarter={q}&year={y}",
                note=f"FMP earnings transcript ({label})",
            ))

        data = {
            "ticker": ticker,
            "quarters_fetched": quarters_fetched,
            "transcripts": transcripts,
            "available": bool(transcripts),
            "warnings": warnings,
            "fetched_at": now_iso,
        }

        save_tool_cache(self.name, ticker, data)

        if not transcripts:
            return ToolResult(
                tool_name=self.name,
                data=data,
                sources=sources,
                confidence="low",
            )

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=sources,
            confidence="high" if len(transcripts) >= 2 else "medium",
        )


def _build_sources(ticker: str, quarters_fetched: List[str], cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    for label in quarters_fetched:
        try:
            y, q = label.split("Q")
            url = f"{FMP_BASE}/{ticker}?quarter={int(q)}&year={int(y)}"
        except Exception:
            url = None
        sources.append(Source(
            tool="transcripts",
            field=f"transcripts:{label}",
            fetched_at=now,
            url=url,
            note=f"FMP earnings transcript ({label}){suffix}",
        ))
    return sources


register(TranscriptsTool())

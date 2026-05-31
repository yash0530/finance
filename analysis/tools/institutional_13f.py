"""
tools.institutional_13f — Top institutional holders for a ticker via yfinance.

13F filings are quarterly, so this tool uses yfinance's pre-aggregated
institutional/mutual-fund holder tables as the simplest reliable free source.
Q/Q delta is not computed (yfinance only returns the latest snapshot); we
mark holders that are new vs. our prior cached snapshot.

Persists each holder row to institutional_holdings_cache. Cached 7 days.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_connection, get_tool_cache, save_tool_cache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _df_to_rows(df) -> List[Dict[str, Any]]:
    """Best-effort DataFrame → list[dict]; tolerant of missing pandas."""
    if df is None:
        return []
    try:
        import pandas as pd
        if not isinstance(df, pd.DataFrame):
            return []
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


def _prior_holder_names(ticker: str, current_quarter: str) -> set:
    """Return set of holder names previously cached for this ticker."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT holder_name FROM institutional_holdings_cache "
            "WHERE ticker = ? AND quarter != ?",
            (ticker, current_quarter),
        ).fetchall()
        return {(r["holder_name"] or "").strip() for r in rows}
    finally:
        conn.close()


def _persist_holders(ticker: str, quarter: str, holders: List[Dict[str, Any]]) -> None:
    if not holders:
        return
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.executemany(
            """INSERT INTO institutional_holdings_cache
               (ticker, quarter, holder_name, shares, value_usd,
                pct_of_holder_assets, qoq_delta_shares, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    ticker, quarter,
                    h.get("name") or "",
                    _safe_float(h.get("shares")) or 0.0,
                    _safe_float(h.get("value_usd")) or 0.0,
                    _safe_float(h.get("pct_float")),
                    None,  # qoq_delta_shares unknown
                    now,
                )
                for h in holders
            ],
        )
        conn.commit()
    finally:
        conn.close()


def _current_quarter_label() -> str:
    d = datetime.now()
    return f"{d.year}Q{((d.month - 1) // 3) + 1}"


def _normalise_holders(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize columns from yfinance institutional_holders / mutualfund_holders."""
    out: List[Dict[str, Any]] = []
    for r in rows:
        # yfinance uses keys like "Holder", "Shares", "Date Reported", "% Out", "Value"
        name = r.get("Holder") or r.get("holder") or r.get("name") or ""
        shares = _safe_float(r.get("Shares") or r.get("shares"))
        value = _safe_float(r.get("Value") or r.get("value"))
        pct_out = _safe_float(r.get("% Out") or r.get("pctHeld") or r.get("pct_out"))
        as_of = r.get("Date Reported") or r.get("dateReported") or ""
        if hasattr(as_of, "isoformat"):
            try:
                as_of = as_of.isoformat()
            except Exception:
                as_of = str(as_of)
        else:
            as_of = str(as_of)
        out.append({
            "name": str(name).strip(),
            "shares": int(shares) if shares is not None else 0,
            "value_usd": value or 0.0,
            "pct_float": pct_out,
            "as_of": as_of,
        })
    return out


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class Institutional13FTool(Tool):
    name = "institutional_13f"
    description = (
        "Top institutional + mutual-fund holders for a US-listed ticker via "
        "yfinance. Provides name, shares, $ value, % float, as-of date. Flags "
        "holders that are new vs. our prior cached snapshot. Q/Q delta not "
        "computed (yfinance limitation). Cached 7 days."
    )
    cache_ttl_seconds = 7 * 24 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        now_iso = datetime.now().isoformat()

        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached=True),
                confidence="high",
                cached=True,
            )

        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            inst_df = getattr(t, "institutional_holders", None)
            mf_df = getattr(t, "mutualfund_holders", None)
            major_df = getattr(t, "major_holders", None)
        except Exception as e:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"yfinance unavailable: {type(e).__name__}: {e}",
                confidence="low",
            )

        inst_rows = _normalise_holders(_df_to_rows(inst_df))
        mf_rows = _normalise_holders(_df_to_rows(mf_df))

        # Merge by name, prefer institutional row but include mutual-fund-only holders
        merged_by_name: Dict[str, Dict[str, Any]] = {}
        for r in inst_rows + mf_rows:
            key = r["name"].lower()
            if key and key not in merged_by_name:
                merged_by_name[key] = r
        merged = list(merged_by_name.values())

        # Sort by value desc
        merged.sort(key=lambda r: r.get("value_usd") or 0, reverse=True)

        quarter = _current_quarter_label()
        prior_names = _prior_holder_names(ticker, quarter)

        for r in merged:
            r["is_new"] = bool(r["name"]) and r["name"] not in prior_names

        # Total institutional pct from major_holders (when present)
        total_inst_pct: Optional[float] = None
        major_rows = _df_to_rows(major_df)
        # yfinance major_holders historically returns a 2-col DF (value, label);
        # try a few shapes.
        try:
            for row in major_rows:
                # Look for a value associated with "institutions"
                label = " ".join(str(v).lower() for v in row.values())
                if "institution" in label and "%" in label:
                    # Extract first numeric from values
                    for v in row.values():
                        sv = str(v).replace("%", "").strip()
                        f = _safe_float(sv)
                        if f is not None and 0 < f <= 100:
                            total_inst_pct = f
                            break
                if total_inst_pct is not None:
                    break
        except Exception:
            total_inst_pct = None

        if not merged:
            data = {
                "ticker": ticker,
                "top_holders": [],
                "total_institutional_pct": total_inst_pct,
                "count_holders": 0,
                "fetched_at": now_iso,
            }
            save_tool_cache(self.name, ticker, data)
            return ToolResult(
                tool_name=self.name,
                data=data,
                sources=_build_sources(ticker, cached=False),
                confidence="low",
            )

        try:
            _persist_holders(ticker, quarter, merged)
        except Exception as e:
            logger.warning(f"Failed to persist institutional holdings: {e}")

        data = {
            "ticker": ticker,
            "top_holders": merged,
            "total_institutional_pct": total_inst_pct,
            "count_holders": len(merged),
            "fetched_at": now_iso,
        }
        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, cached=False),
            confidence="high" if len(merged) >= 5 else "medium",
        )


def _build_sources(ticker: str, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    url = f"https://finance.yahoo.com/quote/{ticker}/holders"
    return [
        Source(
            tool="institutional_13f",
            field="top_holders",
            fetched_at=now,
            url=url,
            note=f"yfinance institutional_holders + mutualfund_holders{suffix}",
        ),
        Source(
            tool="institutional_13f",
            field="total_institutional_pct",
            fetched_at=now,
            url=url,
            note=f"yfinance major_holders{suffix}",
        ),
    ]


register(Institutional13FTool())

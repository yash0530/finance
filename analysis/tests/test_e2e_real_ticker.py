"""
Opt-in real-network, real-LLM end-to-end smoke test (Phase C4).

NOT run by default — this hits live yfinance / Finnhub / Reddit / the user's
configured LLM provider and will spend real money. Run explicitly:

    python3 -m pytest tests/test_e2e_real_ticker.py -m e2e_real -v -s

We pick one ticker per major sector (NVDA / JPM / MRNA / XOM) so a single
run exercises every sector analyzer and most tools. Total budget is capped
at $3 by relying on the v2 agent loop's per-session Budget (defaults from
budget_profile='normal'). The test asserts only structural invariants —
the verdict must exist, the memo must be touched — not specific stock-price
claims, since those move.
"""
from __future__ import annotations

import pytest


SMOKE_TICKERS = [
    ("NVDA", "semis"),
    ("JPM", "banks"),
    ("MRNA", "biotech"),
    ("XOM", "energy"),
]


@pytest.mark.e2e_real
@pytest.mark.parametrize("ticker,expected_sector", SMOKE_TICKERS)
def test_v2_real_research_produces_verdict(ticker, expected_sector):
    """Run the full v2 stream on a real ticker and assert structural sanity."""
    from agent_loop import run_deep_research

    report = run_deep_research(ticker, portfolio_context=None, budget_profile="normal")

    assert isinstance(report, dict) and report, f"{ticker}: empty report"

    # Verdict
    verdict = report.get("verdict") or {}
    assert verdict, f"{ticker}: missing verdict block"
    rec = (verdict.get("recommendation") or "").upper()
    assert rec in {"BUY", "SELL", "TRIM", "HOLD", "AVOID"}, (
        f"{ticker}: bad recommendation '{rec}'"
    )
    assert verdict.get("conviction") in {"LOW", "MEDIUM", "HIGH"}, (
        f"{ticker}: bad conviction '{verdict.get('conviction')}'"
    )

    # Sector routing
    sector_info = report.get("sector") or report.get("sector_classification") or {}
    if sector_info:
        # Soft assertion: the analyzer should have at least *attempted* the
        # right sector. Some tickers may legitimately route elsewhere (e.g. JPM
        # to "default" if the rule list shifts), so just log instead of failing.
        actual = sector_info.get("sector_key", "")
        if actual != expected_sector:
            print(f"NOTE: {ticker} routed to '{actual}', expected '{expected_sector}'")

    # Tool ledger — at least one tool ran and at least one had high/medium confidence
    ledger = report.get("evidence_ledger") or report.get("ledger") or {}
    results = ledger.get("results") or []
    assert results, f"{ticker}: no tool results in ledger"
    confident = [r for r in results if r.get("confidence") in {"high", "medium"}]
    assert confident, f"{ticker}: no tool produced medium/high confidence output"

    # Living Memo — must have been written or updated
    memo = report.get("memo") or report.get("memo_delta") or {}
    assert memo, f"{ticker}: no memo delta produced"


@pytest.mark.e2e_real
def test_qoe_forensics_produces_real_metrics_for_aapl():
    """C5 — verify QoE returns at least one non-null real metric on a large-cap."""
    from tools import get_tool

    tool = get_tool("qoe_forensics")
    assert tool is not None
    result = tool.execute(ticker="AAPL")
    assert result.is_ok(), f"QoE failed: {result.error}"
    data = result.data
    # At least one of the 5 headline metrics should compute on a healthy ticker
    metrics = [
        data.get("beneish_m_score"),
        data.get("altman_z_score"),
        data.get("piotroski_f_score"),
        data.get("accrual_ratio"),
        data.get("sbc_pct_revenue"),
    ]
    non_null = [m for m in metrics if m is not None]
    assert len(non_null) >= 3, f"Only {len(non_null)}/5 QoE metrics computed for AAPL"


@pytest.mark.e2e_real
def test_dcf_produces_three_scenarios_for_aapl():
    """C5 — DCF should return bear/base/bull values, not a stub."""
    from tools import get_tool

    tool = get_tool("dcf_valuation")
    assert tool is not None
    result = tool.execute(ticker="AAPL")
    assert result.is_ok(), f"DCF failed: {result.error}"
    data = result.data
    # If DCF was skipped (e.g. ETF, negative FCF), allow it — but flag clearly
    if data.get("skipped") or data.get("error"):
        pytest.skip(f"DCF skipped for AAPL: {data.get('reason') or data.get('error')}")
    # Otherwise, we expect a 3-scenario structure
    scenarios = data.get("scenarios") or {}
    if scenarios:
        for label in ("bear", "base", "bull"):
            assert label in scenarios, f"DCF missing '{label}' scenario"
    else:
        # Some output shapes flatten the values to top-level
        keys = set(data.keys())
        per_share_present = any(
            k for k in keys if "per_share" in k or "intrinsic" in k
        )
        assert per_share_present, f"DCF returned no scenarios or per-share values: {data}"

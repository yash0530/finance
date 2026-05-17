"""
test_rebalancing_engine.py — B2 holdings-aware rebalance tests.

These tests use research_overrides to avoid DB writes and keep the engine
deterministic.
"""

from datetime import datetime, timedelta, timezone
import pytest

import rebalancing_engine as engine


def _rec(
    ticker, recommendation="BUY", conviction="MEDIUM",
    age_days=2, report_id=None, thesis="thesis text",
    target_low=100.0, target_high=150.0, price=120.0,
):
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    return {
        "ticker": ticker.upper(),
        "report_id": report_id or f"rep-{ticker.lower()}",
        "recommendation": recommendation,
        "conviction": conviction,
        "thesis_summary": thesis,
        "target_low": target_low,
        "target_high": target_high,
        "stop_loss": price * 0.85,
        "price_at_recommendation": price,
        "created_at": created,
    }


def test_empty_portfolio_returns_no_actions():
    out = engine.analyze_portfolio([], profile="moderate", research_overrides={})
    assert out["actions"] == []
    assert out["issues"] == []
    assert out["research_coverage"] == {"with_research": 0, "without_research": 0}


def test_sell_research_emits_exit():
    holdings = [{"ticker": "NVDA", "current_value": 5000, "weight_pct": 10.0}]
    overrides = {"NVDA": _rec("NVDA", "SELL", "HIGH")}
    out = engine.analyze_portfolio(holdings, "aggressive", research_overrides=overrides)

    ticker_actions = [a for a in out["actions"] if a["ticker"] == "NVDA"]
    assert len(ticker_actions) == 1
    a = ticker_actions[0]
    assert a["action"] == "EXIT"
    assert a["urgency"] == "high"
    assert a["source"] == "research"
    assert a["research"]["recommendation"] == "SELL"
    assert a["research"]["stale"] is False


def test_buy_below_cap_emits_add():
    holdings = [{"ticker": "AAPL", "current_value": 4000, "weight_pct": 8.0}]
    overrides = {"AAPL": _rec("AAPL", "BUY", "HIGH")}
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    assert out["actions"][0]["action"] == "ADD"
    assert out["actions"][0]["urgency"] == "high"


def test_buy_over_cap_still_trims_for_concentration():
    holdings = [{"ticker": "TSLA", "current_value": 18000, "weight_pct": 18.0}]
    overrides = {"TSLA": _rec("TSLA", "BUY", "HIGH")}
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    a = out["actions"][0]
    assert a["action"] == "TRIM"
    assert a["research"]["recommendation"] == "BUY"  # research still cited
    assert any(i["type"] == "overweight" for i in out["issues"])


def test_hold_within_cap_emits_hold_no_action_urgency():
    holdings = [{"ticker": "MSFT", "current_value": 5000, "weight_pct": 10.0}]
    overrides = {"MSFT": _rec("MSFT", "HOLD", "MEDIUM")}
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    a = out["actions"][0]
    assert a["action"] == "HOLD"
    assert a["urgency"] == "low"
    assert a["source"] == "research"


def test_no_research_overweight_emits_mechanical_trim():
    holdings = [{"ticker": "META", "current_value": 20000, "weight_pct": 20.0}]
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides={})

    a = out["actions"][0]
    assert a["action"] == "TRIM"
    assert a["source"] == "mechanical"
    assert a["research"] is None
    assert "No research on file" in a["reason"]


def test_no_research_big_loser_emits_review():
    holdings = [{
        "ticker": "PYPL",
        "current_value": 3000,
        "weight_pct": 5.0,
        "unrealized_pnl_pct": -42.0,
    }]
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides={})

    a = out["actions"][0]
    assert a["action"] == "REVIEW"
    assert a["urgency"] == "high"
    assert a["source"] == "mechanical"


def test_stale_research_is_flagged():
    holdings = [{"ticker": "GOOG", "current_value": 5000, "weight_pct": 10.0}]
    overrides = {"GOOG": _rec("GOOG", "BUY", "HIGH", age_days=60)}
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    a = out["actions"][0]
    assert a["research"]["stale"] is True
    assert "stale" in a["reason"].lower() or "old" in a["reason"].lower()


def test_underdiversified_emits_portfolio_level_add():
    # 3 small uncorrelated positions, moderate profile wants 10
    holdings = [
        {"ticker": "AAPL", "current_value": 1000, "weight_pct": 33.3},
        {"ticker": "MSFT", "current_value": 1000, "weight_pct": 33.3},
        {"ticker": "GOOG", "current_value": 1000, "weight_pct": 33.3},
    ]
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides={})

    diversification = [a for a in out["actions"] if a["ticker"] is None and a["action"] == "ADD"]
    assert len(diversification) == 1
    assert any(i["type"] == "underdiversified" for i in out["issues"])


def test_research_coverage_tracks_split():
    holdings = [
        {"ticker": "AAPL", "current_value": 5000, "weight_pct": 10.0},
        {"ticker": "MSFT", "current_value": 5000, "weight_pct": 10.0},
        {"ticker": "GOOG", "current_value": 5000, "weight_pct": 10.0},
    ]
    overrides = {
        "AAPL": _rec("AAPL", "BUY", "HIGH"),
        "MSFT": _rec("MSFT", "HOLD", "MEDIUM"),
    }
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    assert out["research_coverage"]["with_research"] == 2
    assert out["research_coverage"]["without_research"] == 1


def test_unknown_profile_defaults_to_moderate():
    holdings = [{"ticker": "AAPL", "current_value": 5000, "weight_pct": 10.0}]
    out = engine.analyze_portfolio(holdings, "nonsense", research_overrides={})
    assert out["profile"] == "moderate"
    assert out["rules"]["max_single"] == 15.0


def test_actions_sorted_by_urgency():
    holdings = [
        {"ticker": "AAA", "current_value": 5000, "weight_pct": 10.0},
        {"ticker": "BBB", "current_value": 5000, "weight_pct": 10.0},
        {"ticker": "CCC", "current_value": 5000, "weight_pct": 10.0},
    ]
    overrides = {
        "AAA": _rec("AAA", "HOLD", "MEDIUM"),    # low
        "BBB": _rec("BBB", "SELL", "HIGH"),      # high
        "CCC": _rec("CCC", "BUY",  "MEDIUM"),    # medium
    }
    out = engine.analyze_portfolio(holdings, "moderate", research_overrides=overrides)

    urgencies = [a["urgency"] for a in out["actions"]]
    order = {"high": 0, "medium": 1, "low": 2}
    assert urgencies == sorted(urgencies, key=lambda u: order[u])

#!/usr/bin/env python3
"""
rebalancing_engine.py — Portfolio optimization and rebalancing logic.

Evaluates a given portfolio against predefined risk profiles
and returns specific action items (TRIM, ADD, REVIEW) to bring
the portfolio back into alignment.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

RISK_PROFILES = {
    "conservative": {"max_single": 10.0, "max_sector": 25.0, "min_positions": 15},
    "moderate":     {"max_single": 15.0, "max_sector": 35.0, "min_positions": 10},
    "aggressive":   {"max_single": 25.0, "max_sector": 50.0, "min_positions": 5},
}

def analyze_portfolio(holdings: List[Dict], profile: str = "moderate") -> Dict:
    """Analyze holdings against a risk profile and recommend rebalancing actions.

    Args:
        holdings: List of portfolio holdings from portfolio_service
        profile: 'conservative', 'moderate', or 'aggressive'

    Returns:
        Dict containing 'issues' and 'actions'.
    """
    if profile not in RISK_PROFILES:
        profile = "moderate"
    
    rules = RISK_PROFILES[profile]
    
    total_value = sum(h.get("current_value", 0) for h in holdings)
    
    issues = []
    actions = []
    
    if total_value <= 0 or not holdings:
        return {"issues": [], "actions": []}

    # 1. Check for single position concentration
    for h in holdings:
        val = h.get("current_value", 0)
        pct = (val / total_value) * 100 if total_value > 0 else 0
        
        # Override with weight_pct if enriched
        if h.get("weight_pct") is not None:
            pct = h["weight_pct"]
            
        if pct > rules["max_single"]:
            issues.append({"type": "overweight", "ticker": h["ticker"], "pct": pct})
            actions.append({
                "action": "TRIM",
                "ticker": h["ticker"],
                "reason": f"{pct:.1f}% weight exceeds {rules['max_single']}% limit for {profile} profile",
                "urgency": "high" if pct > rules["max_single"] * 1.5 else "medium"
            })

    # 2. Check for diversification (number of positions)
    if len(holdings) < rules["min_positions"]:
        issues.append({"type": "underdiversified", "count": len(holdings), "min": rules["min_positions"]})
        actions.append({
            "action": "ADD",
            "ticker": None,
            "reason": f"Only {len(holdings)} positions. Consider adding more to reach {rules['min_positions']} minimum",
            "urgency": "low"
        })
        
    # 3. Check for big losers (down > 20%)
    for h in holdings:
        pnl_pct = h.get("unrealized_pnl_pct")
        if pnl_pct is not None and pnl_pct < -20.0:
            actions.append({
                "action": "REVIEW",
                "ticker": h["ticker"],
                "reason": f"Down {pnl_pct:.1f}%. Evaluate underlying thesis or cut losses",
                "urgency": "high" if pnl_pct < -35.0 else "medium"
            })

    # Sort actions by urgency: high -> medium -> low
    urgency_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda x: urgency_order.get(x["urgency"], 3))
    
    return {
        "profile": profile,
        "rules": rules,
        "issues": issues,
        "actions": actions
    }

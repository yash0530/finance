"""
tools.qoe_forensics — Quality of Earnings forensics.

Pure computation from yfinance annual statements:
  - Beneish M-Score (8-factor earnings manipulation)
  - Altman Z-Score (manufacturing variant, public-company)
  - Piotroski F-Score (0-9 fundamental quality)
  - Accrual ratio (NI - CFO) / Assets
  - SBC % of revenue

Cached 24h.  No network beyond yfinance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import Source, Tool, ToolResult, register
from db import get_tool_cache, save_tool_cache


# ── Field-name candidates (yfinance labels vary by company/version) ────────

INCOME_KEYS = {
    "revenue":      ["Total Revenue", "Revenue", "TotalRevenue"],
    "gross_profit": ["Gross Profit", "GrossProfit"],
    "sga":          ["Selling General And Administration",
                     "Selling General And Administrative",
                     "SellingGeneralAndAdministration"],
    "depreciation": ["Reconciled Depreciation", "Depreciation",
                     "Depreciation And Amortization",
                     "DepreciationAmortizationDepletion"],
    "ebit":         ["EBIT", "Operating Income", "OperatingIncome"],
    "net_income":   ["Net Income", "NetIncome", "Net Income Common Stockholders"],
}

BALANCE_KEYS = {
    "receivables":     ["Accounts Receivable", "Receivables", "AccountsReceivable",
                        "Net Receivables"],
    "current_assets":  ["Current Assets", "Total Current Assets", "CurrentAssets"],
    "ppe":             ["Net PPE", "Property Plant Equipment Net", "Net Property Plant And Equipment",
                        "NetPPE"],
    "total_assets":    ["Total Assets", "TotalAssets"],
    "current_liab":    ["Current Liabilities", "Total Current Liabilities", "CurrentLiabilities"],
    "long_term_debt":  ["Long Term Debt", "LongTermDebt"],
    "total_liab":      ["Total Liabilities Net Minority Interest", "Total Liab",
                        "Total Liabilities", "TotalLiabilitiesNetMinorityInterest"],
    "working_capital": ["Working Capital", "WorkingCapital"],
    "retained_earn":   ["Retained Earnings", "RetainedEarnings"],
    "shares_out":      ["Share Issued", "Ordinary Shares Number", "Common Stock Equity",
                        "ShareIssued"],
}

CASHFLOW_KEYS = {
    "cfo":            ["Operating Cash Flow", "Total Cash From Operating Activities",
                       "Cash Flow From Continuing Operating Activities",
                       "OperatingCashFlow"],
    "sbc":            ["Stock Based Compensation", "StockBasedCompensation"],
}


def _lookup(df, candidates: List[str], col_idx: int) -> Optional[float]:
    """Return a numeric value from a yfinance DataFrame (rows=line items, cols=years)."""
    if df is None or df.empty:
        return None
    if col_idx >= len(df.columns):
        return None
    col = df.columns[col_idx]
    for name in candidates:
        if name in df.index:
            try:
                val = df.loc[name, col]
                if val is None:
                    continue
                # Pandas may return Series if duplicate index — take first
                if hasattr(val, "iloc"):
                    val = val.iloc[0]
                fv = float(val)
                if fv != fv:  # NaN
                    return None
                return fv
            except (TypeError, ValueError):
                continue
    return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    try:
        if b == 0:
            return None
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


# ── Metric computations ───────────────────────────────────────────────────

def _beneish_m_score(inc, bal, cf) -> Dict[str, Any]:
    """Compute Beneish M-Score comparing year t (col 0) vs t-1 (col 1)."""
    warnings: List[str] = []

    rev_t  = _lookup(inc, INCOME_KEYS["revenue"], 0)
    rev_p  = _lookup(inc, INCOME_KEYS["revenue"], 1)
    gp_t   = _lookup(inc, INCOME_KEYS["gross_profit"], 0)
    gp_p   = _lookup(inc, INCOME_KEYS["gross_profit"], 1)
    sga_t  = _lookup(inc, INCOME_KEYS["sga"], 0)
    sga_p  = _lookup(inc, INCOME_KEYS["sga"], 1)
    dep_t  = _lookup(inc, INCOME_KEYS["depreciation"], 0)
    dep_p  = _lookup(inc, INCOME_KEYS["depreciation"], 1)
    ni_t   = _lookup(inc, INCOME_KEYS["net_income"], 0)

    rec_t  = _lookup(bal, BALANCE_KEYS["receivables"], 0)
    rec_p  = _lookup(bal, BALANCE_KEYS["receivables"], 1)
    ca_t   = _lookup(bal, BALANCE_KEYS["current_assets"], 0)
    ca_p   = _lookup(bal, BALANCE_KEYS["current_assets"], 1)
    ppe_t  = _lookup(bal, BALANCE_KEYS["ppe"], 0)
    ppe_p  = _lookup(bal, BALANCE_KEYS["ppe"], 1)
    ta_t   = _lookup(bal, BALANCE_KEYS["total_assets"], 0)
    ta_p   = _lookup(bal, BALANCE_KEYS["total_assets"], 1)
    cl_t   = _lookup(bal, BALANCE_KEYS["current_liab"], 0)
    cl_p   = _lookup(bal, BALANCE_KEYS["current_liab"], 1)
    ltd_t  = _lookup(bal, BALANCE_KEYS["long_term_debt"], 0)
    ltd_p  = _lookup(bal, BALANCE_KEYS["long_term_debt"], 1)

    cfo_t  = _lookup(cf, CASHFLOW_KEYS["cfo"], 0)

    # DSRI = (Rec_t/Sales_t) / (Rec_t-1/Sales_t-1)
    dsri = _safe_div(_safe_div(rec_t, rev_t), _safe_div(rec_p, rev_p))

    # GMI = GM_t-1 / GM_t
    gm_t = _safe_div(gp_t, rev_t)
    gm_p = _safe_div(gp_p, rev_p)
    gmi = _safe_div(gm_p, gm_t)

    # AQI = (1 - (CA+PPE)/TA)_t / same_t-1
    aqi_t = None
    aqi_p = None
    if ca_t is not None and ppe_t is not None and ta_t:
        aqi_t = 1 - (ca_t + ppe_t) / ta_t
    if ca_p is not None and ppe_p is not None and ta_p:
        aqi_p = 1 - (ca_p + ppe_p) / ta_p
    aqi = _safe_div(aqi_t, aqi_p)

    # SGI = Sales_t / Sales_t-1
    sgi = _safe_div(rev_t, rev_p)

    # DEPI = Dep_t-1/(Dep_t-1+PPE_t-1) / same_t
    depi_t = _safe_div(dep_t, (dep_t + ppe_t) if (dep_t is not None and ppe_t is not None) else None)
    depi_p = _safe_div(dep_p, (dep_p + ppe_p) if (dep_p is not None and ppe_p is not None) else None)
    depi = _safe_div(depi_p, depi_t)

    # SGAI = (SGA/Sales)_t / (SGA/Sales)_t-1
    sgai = _safe_div(_safe_div(sga_t, rev_t), _safe_div(sga_p, rev_p))

    # TATA = (NI - CFO) / TA   for year t
    if ni_t is not None and cfo_t is not None and ta_t:
        tata = (ni_t - cfo_t) / ta_t
    else:
        tata = None

    # LVGI = (LTD+CL)/TA _t / same _t-1
    lvgi_t = _safe_div(((ltd_t or 0) + (cl_t or 0)) if (ltd_t is not None or cl_t is not None) else None, ta_t)
    lvgi_p = _safe_div(((ltd_p or 0) + (cl_p or 0)) if (ltd_p is not None or cl_p is not None) else None, ta_p)
    lvgi = _safe_div(lvgi_t, lvgi_p)

    factors = {"DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
               "DEPI": depi, "SGAI": sgai, "TATA": tata, "LVGI": lvgi}

    missing = [k for k, v in factors.items() if v is None]
    if missing:
        warnings.append(f"Beneish: missing factors {missing}")
        return {"score": None, "verdict": "insufficient_data", "factors": factors, "warnings": warnings}

    m = (-4.84
         + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)

    if m > -1.78:
        verdict = "possible manipulation"
    elif m < -2.22:
        verdict = "unlikely manipulation"
    else:
        verdict = "grey zone"

    return {"score": round(m, 3), "verdict": verdict, "factors": factors, "warnings": warnings}


def _altman_z(inc, bal, info) -> Dict[str, Any]:
    """Compute Altman Z-Score (public manufacturing variant)."""
    warnings: List[str] = []
    wc = _lookup(bal, BALANCE_KEYS["working_capital"], 0)
    if wc is None:
        ca = _lookup(bal, BALANCE_KEYS["current_assets"], 0)
        cl = _lookup(bal, BALANCE_KEYS["current_liab"], 0)
        if ca is not None and cl is not None:
            wc = ca - cl
    ta = _lookup(bal, BALANCE_KEYS["total_assets"], 0)
    re = _lookup(bal, BALANCE_KEYS["retained_earn"], 0)
    ebit = _lookup(inc, INCOME_KEYS["ebit"], 0)
    rev = _lookup(inc, INCOME_KEYS["revenue"], 0)
    tl = _lookup(bal, BALANCE_KEYS["total_liab"], 0)

    mcap = None
    if isinstance(info, dict):
        mcap = info.get("marketCap")

    A = _safe_div(wc, ta)
    B = _safe_div(re, ta)
    C = _safe_div(ebit, ta)
    D = _safe_div(mcap, tl)
    E = _safe_div(rev, ta)

    parts = {"A": A, "B": B, "C": C, "D": D, "E": E}
    missing = [k for k, v in parts.items() if v is None]
    if missing:
        warnings.append(f"Altman: missing components {missing}")
        return {"score": None, "verdict": "insufficient_data", "components": parts, "warnings": warnings}

    z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E
    if z > 2.99:
        verdict = "safe"
    elif z >= 1.81:
        verdict = "grey"
    else:
        verdict = "distress"
    return {"score": round(z, 3), "verdict": verdict, "components": parts, "warnings": warnings}


def _piotroski(inc, bal, cf) -> Dict[str, Any]:
    """Compute Piotroski F-Score (0..9). Returns score and per-criterion booleans."""
    warnings: List[str] = []
    comp: Dict[str, Optional[bool]] = {}

    ni_t  = _lookup(inc, INCOME_KEYS["net_income"], 0)
    ni_p  = _lookup(inc, INCOME_KEYS["net_income"], 1)
    cfo_t = _lookup(cf, CASHFLOW_KEYS["cfo"], 0)
    ta_t  = _lookup(bal, BALANCE_KEYS["total_assets"], 0)
    ta_p  = _lookup(bal, BALANCE_KEYS["total_assets"], 1)

    rev_t = _lookup(inc, INCOME_KEYS["revenue"], 0)
    rev_p = _lookup(inc, INCOME_KEYS["revenue"], 1)
    gp_t  = _lookup(inc, INCOME_KEYS["gross_profit"], 0)
    gp_p  = _lookup(inc, INCOME_KEYS["gross_profit"], 1)

    ltd_t = _lookup(bal, BALANCE_KEYS["long_term_debt"], 0)
    ltd_p = _lookup(bal, BALANCE_KEYS["long_term_debt"], 1)
    ca_t  = _lookup(bal, BALANCE_KEYS["current_assets"], 0)
    ca_p  = _lookup(bal, BALANCE_KEYS["current_assets"], 1)
    cl_t  = _lookup(bal, BALANCE_KEYS["current_liab"], 0)
    cl_p  = _lookup(bal, BALANCE_KEYS["current_liab"], 1)
    sh_t  = _lookup(bal, BALANCE_KEYS["shares_out"], 0)
    sh_p  = _lookup(bal, BALANCE_KEYS["shares_out"], 1)

    # Profitability
    comp["positive_net_income"] = (ni_t is not None and ni_t > 0)
    comp["positive_cfo"] = (cfo_t is not None and cfo_t > 0)
    roa_t = _safe_div(ni_t, ta_t)
    roa_p = _safe_div(ni_p, ta_p)
    comp["roa_improved"] = (roa_t is not None and roa_p is not None and roa_t > roa_p)
    comp["cfo_gt_ni"] = (cfo_t is not None and ni_t is not None and cfo_t > ni_t)

    # Leverage / liquidity
    comp["lt_debt_fell"] = (ltd_t is not None and ltd_p is not None and ltd_t < ltd_p)
    cr_t = _safe_div(ca_t, cl_t)
    cr_p = _safe_div(ca_p, cl_p)
    comp["current_ratio_improved"] = (cr_t is not None and cr_p is not None and cr_t > cr_p)
    comp["no_share_issuance"] = (sh_t is not None and sh_p is not None and sh_t <= sh_p)

    # Operating efficiency
    gm_t = _safe_div(gp_t, rev_t)
    gm_p = _safe_div(gp_p, rev_p)
    comp["gross_margin_improved"] = (gm_t is not None and gm_p is not None and gm_t > gm_p)
    at_t = _safe_div(rev_t, ta_t)
    at_p = _safe_div(rev_p, ta_p)
    comp["asset_turnover_improved"] = (at_t is not None and at_p is not None and at_t > at_p)

    score = sum(1 for v in comp.values() if v is True)
    return {"score": score, "components": comp, "warnings": warnings}


def _accrual_ratio(inc, bal, cf) -> Dict[str, Any]:
    ni  = _lookup(inc, INCOME_KEYS["net_income"], 0)
    cfo = _lookup(cf, CASHFLOW_KEYS["cfo"], 0)
    ta  = _lookup(bal, BALANCE_KEYS["total_assets"], 0)
    if ni is None or cfo is None or not ta:
        return {"ratio": None, "flag": False}
    ratio = (ni - cfo) / ta
    return {"ratio": round(ratio, 4), "flag": ratio > 0.10}


def _sbc_pct(inc, cf) -> Dict[str, Any]:
    sbc = _lookup(cf, CASHFLOW_KEYS["sbc"], 0)
    rev = _lookup(inc, INCOME_KEYS["revenue"], 0)
    if sbc is None or not rev:
        return {"pct": None, "flag": False}
    pct = sbc / rev
    return {"pct": round(pct, 4), "flag": pct > 0.15}


# ── Tool class ────────────────────────────────────────────────────────────

class QoEForensicsTool(Tool):
    name = "qoe_forensics"
    description = (
        "Quality-of-earnings forensics from yfinance annual financials: "
        "Beneish M-Score (manipulation), Altman Z-Score (distress), "
        "Piotroski F-Score (fundamental quality), accrual ratio, and "
        "SBC as % of revenue. Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
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
        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name, data=cached,
                sources=_build_sources(ticker, cached, cached=True),
                confidence=cached.get("_confidence", "medium"),
                cached=True,
            )

        import yfinance as yf
        tk = yf.Ticker(ticker)
        try:
            inc = tk.income_stmt
        except Exception:
            inc = None
        try:
            bal = tk.balance_sheet
        except Exception:
            bal = None
        try:
            cf = tk.cashflow
        except Exception:
            cf = None
        try:
            info = tk.info or {}
        except Exception:
            info = {}

        warnings: List[str] = []
        for name, df in (("income_stmt", inc), ("balance_sheet", bal), ("cashflow", cf)):
            if df is None or getattr(df, "empty", True):
                warnings.append(f"{name} unavailable from yfinance")

        beneish = _beneish_m_score(inc, bal, cf)
        altman  = _altman_z(inc, bal, info)
        piotr   = _piotroski(inc, bal, cf)
        accr    = _accrual_ratio(inc, bal, cf)
        sbc     = _sbc_pct(inc, cf)

        warnings.extend(beneish.get("warnings", []))
        warnings.extend(altman.get("warnings", []))
        warnings.extend(piotr.get("warnings", []))

        # Identify year analyzed (col 0 of income stmt)
        year_analyzed = None
        try:
            if inc is not None and not inc.empty:
                year_analyzed = str(inc.columns[0])[:10]
        except Exception:
            pass

        # Build human-readable warnings
        human: List[str] = []
        if beneish.get("score") is not None and beneish["verdict"] == "possible manipulation":
            human.append(f"Beneish M-Score {beneish['score']} suggests possible earnings manipulation")
        if altman.get("score") is not None and altman["verdict"] == "distress":
            human.append(f"Altman Z-Score {altman['score']} indicates financial distress zone")
        if accr.get("flag"):
            human.append(f"Accrual ratio {accr['ratio']} above 0.10 — earnings quality concern")
        if sbc.get("flag"):
            human.append(f"SBC at {round((sbc['pct'] or 0)*100, 1)}% of revenue exceeds 15% threshold")

        # Missing-metric count drives confidence
        missing_count = sum(
            1 for v in (beneish.get("score"), altman.get("score"),
                        accr.get("ratio"), sbc.get("pct"))
            if v is None
        )
        confidence = "medium" if missing_count <= 2 else "low"

        data: Dict[str, Any] = {
            "beneish_m_score": beneish.get("score"),
            "beneish_verdict": beneish.get("verdict"),
            "beneish_factors": beneish.get("factors"),
            "altman_z_score": altman.get("score"),
            "altman_verdict": altman.get("verdict"),
            "altman_components": altman.get("components"),
            "piotroski_f_score": piotr.get("score"),
            "piotroski_components": piotr.get("components"),
            "accrual_ratio": accr.get("ratio"),
            "accrual_flag": accr.get("flag"),
            "sbc_pct_revenue": sbc.get("pct"),
            "sbc_flag": sbc.get("flag"),
            "year_analyzed": year_analyzed,
            "warnings": human + warnings,
            "_confidence": confidence,
        }

        save_tool_cache(self.name, ticker, data)

        return ToolResult(
            tool_name=self.name, data=data,
            sources=_build_sources(ticker, data, cached=False),
            confidence=confidence,
        )


def _build_sources(ticker: str, data: Dict, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    url = f"https://finance.yahoo.com/quote/{ticker}/financials"
    suffix = " (cached)" if cached else ""
    sources: List[Source] = []
    metric_notes = {
        "beneish_m_score":   "Beneish M-score computed from 2y income/balance/cashflow",
        "altman_z_score":    "Altman Z-score computed from income/balance + market cap",
        "piotroski_f_score": "Piotroski F-score computed from 2y income/balance/cashflow",
        "accrual_ratio":     "Accrual ratio (NI-CFO)/Assets from yfinance financials",
        "sbc_pct_revenue":   "SBC % revenue from yfinance cashflow statement",
    }
    for field_name, note in metric_notes.items():
        if data.get(field_name) is not None:
            sources.append(Source(
                tool="qoe_forensics", field=field_name,
                fetched_at=now, url=url, note=note + suffix,
            ))
    return sources


register(QoEForensicsTool())

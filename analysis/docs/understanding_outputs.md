---
title: Understanding the Outputs
order: 3
category: Daily use
---

# Understanding the Outputs

How to read what the tool produces, what each piece *actually means*, and when to override it.

---

## The Verdict block

Every Deep Research v2 run ends with a structured verdict:

```
RECOMMENDATION:  BUY | SELL | TRIM | HOLD | AVOID
CONVICTION:      LOW | MEDIUM | HIGH
SUGGESTED SIZE:  N% of book
ENTRY:           $X.XX (or a range)
STOP:            $X.XX
TARGET (12m):    $X.XX
THESIS:          one paragraph
WHAT WOULD CHANGE MY MIND: bullet list of falsifiability criteria
```

### Recommendation

- **BUY** — open a new position or add to an existing one. Conviction determines size.
- **SELL** — exit fully. Used when the thesis is broken or the risk/reward has flipped.
- **TRIM** — reduce position size (typically because the position has appreciated past the suggested weight, *not* because the thesis broke).
- **HOLD** — keep the existing position; no action needed.
- **AVOID** — don't open a new position. Distinct from SELL: avoid is for tickers you don't own.

### Conviction

The conviction band is the tool's confidence in its own thesis, *not* the strength of the buy signal.

- **HIGH** — the tool can point to multiple independent, high-confidence pieces of evidence supporting the thesis; the bear case has been considered and found weaker; no major data gaps. Risk it.
- **MEDIUM** — the thesis is well-supported but with material open questions, or the bull/bear debate is close. Size accordingly.
- **LOW** — significant data gaps, a strong bear case, or low-confidence inputs. Treat as exploratory; either skip or take a token-sized position.

### Suggested size

The tool emits a suggested position size in % of book. **Treat it as a cap, not a target.** See [How to Invest](how-to-invest) for the conservative sizing rules.

### What would change my mind

This is the most important field in the entire output.

These are explicit, falsifiable criteria that — if triggered — should make you exit the position regardless of price action. Examples:
- "Gross margin compresses below 60% in the next two quarters."
- "Inventory days exceed 90 with revenue growth below 10%."
- "Insider selling exceeds $50M in any rolling 30-day window."

The monitor watches these conditions hourly. If any trigger, you'll see it in the Advisor digest with a `severity` rating.

If you can't write a credible "what would change my mind" for a position, you don't have a real thesis — you have hope. Exit.

---

## Calibration math

The **Calibration** page tracks how the tool's recommendations actually performed over time, by conviction and by recommendation type. The math:

- For each recommendation, we record the price on the day it was issued.
- A nightly job populates the return at 1 month, 3 months, 6 months, and 1 year after issuance.
- Hit rate by conviction = % of recommendations that returned positively in the direction the verdict predicted (positive return for BUY, negative for SELL/AVOID, weight-band-respecting for TRIM).

### What "calibrated" means

A perfectly calibrated tool has:
- HIGH-conviction calls hitting at ~70%+ over a meaningful sample (n ≥ 30 per bucket).
- MEDIUM calls hitting at ~50–60%.
- LOW calls hovering near 50% (this is fine — LOW conviction is supposed to be a coin flip).

### What's NOT a calibration

- Fewer than 20 closed recommendations. The Calibration page will show "n too small to trust" until you cross that threshold.
- A 10-call winning streak. That's variance. Variance favors believing you're a genius right before you blow up.

### Why local-LLM runs aren't tracked

If you run Deep Research on Ollama (or any provider flagged `is_local=True` in `llm_settings`), the verdict is **not** persisted to the `recommendations` table. Reason: calibration measures the underlying model. Mixing local and frontier verdicts pollutes the signal and makes the track record meaningless.

This is configurable (`llm_settings.allow_local_for_recommendations`) but the default is OFF and you should leave it that way.

---

## Citations and confidence

Every figure in a research report has a citation marker that points back to the tool that produced it. Click any number to see:
- Which tool returned it
- The tool's confidence rating for that field
- The timestamp the data was fetched
- The URL (if applicable — e.g. SEC filing, Yahoo Finance page)

Confidence ratings:
- **high** — fetched from a primary source (SEC filing, exchange data) within minutes.
- **medium** — derived from primary data, or fetched but with some processing.
- **low** — LLM-extracted from unstructured text, degraded (missing data), or fallback path (e.g. keyword-scored sentiment when the LLM was unavailable).

**If a claim in the report has no citation, treat it as a hallucination and ignore it.** That's a bug; please file it.

---

## When to override the tool

See the matching section in [How to Invest](how-to-invest). Short version:

- **Override** when you have specific non-public knowledge, a macro event the tool didn't capture, or a tax/cash management reason.
- **Don't override** because the verdict "feels wrong" or because you want to take more risk after a winner.

When you do override, write the reason into the Living Memo's `manual_notes` section. Future-you will thank present-you for the audit trail.

---

## Where the numbers come from

| Block in the report | Underlying data source |
|---|---|
| Fundamentals (revenue, margins, ratios) | yfinance `Ticker.info` + financial statements |
| Financial trends (multi-year) | yfinance `income_stmt` / `balance_sheet` / `cashflow` |
| Sentiment (composite 0–10) | Finnhub news + analyst consensus + Reddit + LLM scoring |
| QoE Forensics (Beneish/Altman/Piotroski) | yfinance annual statements, pure computation |
| DCF intrinsic value | yfinance FCF + revenue growth, 3-scenario model |
| Peer comparison | yfinance sector averages (P/E, P/S, P/B) |
| Macro regime | yfinance indices (^TNX, ^VIX, DXY, HYG, ^GSPC) |
| Insider activity | SEC EDGAR Form 4 filings |
| Earnings transcripts | yfinance / Seeking Alpha mirrors when available |

Every fetch is cached (TTLs documented in [Architecture](architecture)). The agent loop's Budget enforces a per-session dollar cap so an exploding LLM call can't bankrupt you.

---

## What to read next

- [How to Invest with This Tool](how-to-invest) — the workflow these outputs feed into.
- [Architecture Overview](architecture) — the engineering view, for when you want to know *why* a number is the way it is.

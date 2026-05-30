---
title: Understanding the Outputs
order: 3
category: Daily use
---

# Understanding the Outputs

How to read what the app produces, what each piece means, and when to distrust it.

---

## The verdict block

A Deep Research run ends with a structured verdict:

```text
RECOMMENDATION:  BUY | SELL | TRIM | HOLD | AVOID
CONVICTION:      LOW | MEDIUM | HIGH
SUGGESTED SIZE:  N% of book
ENTRY:           $X.XX or a range
STOP:            $X.XX
TARGET:          $X.XX
THESIS:          one paragraph
WHAT WOULD CHANGE MY MIND: concrete criteria
```

The verdict is not an order ticket. Treat it as a research conclusion with a sizing cap.

---

## Recommendation

- **BUY** — the setup can justify new capital, subject to sizing and evidence quality.
- **SELL** — the thesis is broken or risk/reward is unattractive.
- **TRIM** — reduce exposure, usually because sizing or upside/downside has changed.
- **HOLD** — no action from the current evidence.
- **AVOID** — do not open a new position.

Context matters. A HOLD can be good news if you already own the stock; it is not a reason to open a position.

---

## Conviction

Conviction is the tool's confidence in its own thesis, not the expected return.

- **HIGH** — multiple independent, high-confidence evidence points; bear case considered; no major gaps.
- **MEDIUM** — supported but with material uncertainties or a close bull/bear debate.
- **LOW** — large gaps, fragile evidence, or a strong unresolved bear case.

Use conviction to cap size, then adjust downward for stale data, weak citations, or your own risk constraints.

---

## Suggested size

Suggested size is a cap. For a small personal book, conservative caps matter more than squeezing every dollar into a thesis. See [How to Invest](how-to-invest) for the default sizing table.

Never let confident wording substitute for cited evidence.

---

## Evidence references

Every material claim from the agents should cite `evidence_refs`. A reference should map to a real tool result in the evidence ledger.

Use citations to answer:

- Which tool produced the evidence?
- When was it fetched?
- Was it direct data, derived computation, or a degraded fallback?
- Did the same claim appear in multiple sources?

If a claim has no evidence reference, treat it as untrusted.

---

## Confidence ratings

Tool confidence is separate from verdict conviction:

- **high** — source resolved cleanly and the field is direct or reliably computed.
- **medium** — useful but derived, partial, or dependent on a weaker source.
- **low** — missing, degraded, fallback, or error-prone.

A HIGH conviction verdict built on low-confidence tool outputs deserves skepticism.

---

## Living Memo

The Living Memo is the app's per-ticker memory. It is a distilled document, not a vector search dump.

Each `/thesis` run can:

- Read the previous memo.
- Identify stale facts and open questions.
- Add new cited findings.
- Propose a memo update.

The memo should get sharper over repeated sessions. History is preserved so you can audit how the thesis changed.

---

## Console command outputs

- **`/why`** — fast explanation of what matters now, with citations.
- **`/thesis`** — full agentic research, debate, verdict, self-critique, and memo update.
- **`/dossier`** — broader ticker context.
- **`/theme`** — theme-level analysis.
- **`/compare`** — relative case across multiple tickers.

Use the lightest command that answers the question. Use `/thesis` before a capital-allocation decision.

---

## Screener outputs

The Screener is deterministic rule logic over selected universes:

- **themes** — tickers in your theme packs.
- **watchlist** — names you track in Terminal.
- **sp500** — cached S&P 500 snapshot for fast fundamentals and relative fields.

Screens find candidates; they do not create theses. Research the survivors before acting.

---

## Where numbers come from

| Output area | Source |
|---|---|
| Fundamentals | yfinance `Ticker.info` and statements |
| Financial trends | yfinance income, balance sheet, and cash-flow data |
| Technicals and patterns | yfinance price history plus local detectors |
| Sentiment and news | Finnhub when configured, yfinance fallback, Reddit where available |
| Filings | SEC EDGAR |
| Insider activity | SEC Form 4 |
| Institutional holders | yfinance holder data |
| Options flow | yfinance and optional premium sources |
| Macro context | yfinance market indices |
| S&P 500 relative fields | `.cache/sp500_data.json`, refreshable from Settings |

Tool TTLs and endpoint details live in [Architecture](architecture) and `next_gen_tool.md`.

---

## When to override

Override only for concrete reasons the tool did not capture: domain knowledge, a very recent event, tax constraints, liquidity needs, or a source you verified manually.

If the override reason cannot be written in one or two precise sentences, it is probably not strong enough to overrule a well-cited thesis.

---

## What to read next

- [How to Invest with This Tool](how-to-invest) — the workflow these outputs feed into.
- [Architecture Overview](architecture) — where the numbers and events come from.

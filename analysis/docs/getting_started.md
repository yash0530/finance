---
title: Getting Started
order: 1
category: Start here
---

# Getting Started

A 5-minute walkthrough from "I just opened the app" to "I have a research view I can act on."

---

## What you're looking at

Portfolio Intelligence is a single-investor research and decision-support tool. It has one primary job: help you turn cited market data and Deep Research output into conservative, auditable decisions.

The current Edge v3 navigation is:

- **Terminal** — market command center: watchlist, theme heat, movers, news, catalysts, flow, and quick hypotheses.
- **Stock View** — ticker-level chart, fundamentals, technicals, sentiment, filings, and theme context.
- **Console** — slash-command research surface for `/thesis`, `/dossier`, `/why`, `/theme`, and `/compare`.
- **Library** — saved research reports and Living Memos.
- **Screener** — rule-based scans over themes, watchlist, or the S&P 500 snapshot.
- **Settings** — LLM provider, data-tier status, S&P 500 snapshot refresh, and theme packs.

The Docs link in the footer opens this guide set.

---

## First-time setup

### 1. Configure an LLM provider

Open **Settings → LLM**. Pick a provider and save the models you want the app to use:

- **Claude** — strongest default for serious research.
- **Gemini** — useful lower-cost cloud option.
- **Ollama** — local exploration when you want zero API spend.

Deep Research should be treated as decision support, not a trading signal generator. Read the cited rationale before acting.

### 2. Check data tiers

Open **Settings → Data Tiers**. The app shows which optional environment keys are present without exposing secrets. The free tier still works through yfinance, Finnhub when configured, and SEC sources.

Use the **S&P 500 snapshot** refresh button when the Screener or S&P sector heatmap needs fresh constituents and fundamentals. Refreshes are pull-triggered only; nothing runs in the background.

### 3. Set up themes and watchlist

Use **Settings → Themes** to maintain theme packs such as AI infrastructure, energy, or cloud software. Use **Terminal** to maintain a watchlist. Themes and watchlist entries feed the Terminal, Screener, and Stock View context panels.

---

## Run your first research

Open **Console** and run:

```text
/thesis NVDA
```

The Console streams the agent loop as it plans, calls tools, debates bull and bear cases, judges the setup, critiques itself, and proposes Living Memo updates. For a faster answer, use:

```text
/why NVDA
```

Use `/thesis` for anything you might size with real money. Use `/why` for a quick, cited read on what matters today.

---

## What to read first

After a research run, open the report and memo from **Library**:

- **Verdict** — recommendation, conviction, sizing cap, targets, stop, and one-paragraph thesis.
- **Bull/Bear/Judge reasoning** — the debate that produced the verdict.
- **Evidence references** — every material claim should cite a tool result.
- **Living Memo** — the evolving per-ticker knowledge document and open questions.

If a claim has no evidence reference, treat it as untrusted.

---

## A simple routine

1. Start in **Terminal** for watchlist moves, theme heat, and news.
2. Open **Stock View** for any ticker that looks interesting.
3. Use **Console `/why`** for a fast cited explanation.
4. Use **Console `/thesis`** before committing capital.
5. Revisit **Library** to compare the new report with the prior Living Memo.
6. Use **Screener** for pull-based idea generation, then research the survivors.

---

## What to read next

- [How to Invest with This Tool](how-to-invest) — the conservative workflow for deploying capital.
- [Understanding the Outputs](understanding-outputs) — how to read verdicts, citations, confidence, and memo updates.
- [Troubleshooting](troubleshooting) — what to do when something breaks.

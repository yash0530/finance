---
title: Getting Started
order: 1
category: Start here
---

# Getting Started

A 5-minute walkthrough from "I just opened the app" to "I have an opinion on a stock I can act on."

---

## What you're looking at

Portfolio Intelligence is a single-investor research tool. It does three things:

1. **Looks at your holdings** and tells you what to do with each one (trim, add, exit, hold) based on the underlying research.
2. **Researches any ticker** end-to-end — fundamentals, financials, technicals, sentiment, sector context, macro regime — and produces a structured verdict you can act on.
3. **Tracks its own calibration** so you can see whether the tool actually deserves your trust over time.

It is not a backtest engine, a screener, or a paper-trading simulator. The output is meant to be acted on with real money — modestly, with full awareness of the tool's limits.

---

## First-time setup

### 1. Connect a portfolio

Open the **Portfolio** page in the left nav. You have three options:

- **Robinhood**: enter your credentials in the modal. The session token is cached locally (`~/.portfolio_intelligence/.cache/rh_session.json`) and never leaves your machine.
- **CSV upload**: drop a CSV with columns `ticker, shares, cost_basis`. Headers are case-insensitive.
- **Manual entry**: click "Add holding" and fill in the form.

Whichever you pick, the holdings show up with live prices, P&L, and weight %.

### 2. Configure an LLM provider

Open **LLM Settings** (gear icon at the bottom of the sidebar). You need at least one:

- **Claude** (Anthropic) — recommended for production use; best calibration.
- **Gemini** (Google) — good cheap fallback; default for monitoring.
- **Ollama** (local) — free, but verdicts from Ollama are NOT persisted to the track record (see [Understanding the Outputs](understanding-outputs)).

Paste the API key, pick `model_fast` (cheap, for monitoring) and `model_deep` (smart, for the actual analysis), save.

### 3. Run your first research

Two paths:

- **Quick Research** (sidebar) — for any ticker, runs the v1 8-stage pipeline. Faster, more deterministic.
- **Deep Research v2** (sidebar) — runs the agentic loop. Slower, more thorough, produces a Living Memo. **This is the one you should use for anything you plan to trade.**

Type a ticker, hit Run, and watch the SSE stream. Each event shows what the tool is doing — which tool is being called, what each agent is concluding, how the budget is being spent.

---

## What you should look at first

When the run finishes, scroll to the bottom:

- **Verdict block**: `BUY / SELL / TRIM / HOLD / AVOID` + conviction (LOW / MEDIUM / HIGH) + suggested position size + targets + stop loss + thesis summary.
- **What would change my mind**: explicit falsifiability conditions. If any of these trigger later, the monitor flags it.
- **Living Memo**: the evolving per-ticker knowledge document. Open it and read it. Every session refines it.

**Do not act on a verdict you haven't read the rationale for.** The tool reasons; you decide.

---

## The 10-minute morning routine

Once you have positions, this is what to do each trading day:

1. Open **Advisor**. Read the digest — any decay signals from overnight?
2. Open **Rebalance**. Scan for TRIM / EXIT actions. If something has triggered a "what would change my mind" condition, you'll see it here with a link to the research.
3. Open **Calibration** weekly. Check the hit rate by conviction. If HIGH-conviction calls are missing more than 40% of the time, lower your sizing.

That's it. Everything else is opt-in.

---

## What to read next

- [How to Invest with This Tool](how-to-invest) — the opinionated workflow for actually deploying capital.
- [Understanding the Outputs](understanding-outputs) — how to read the verdict, calibration math, when to override.
- [Troubleshooting](troubleshooting) — what to do when something breaks.

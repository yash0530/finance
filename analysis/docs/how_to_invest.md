---
title: How to Invest with This Tool
order: 2
category: Start here
---

# How to Invest with This Tool

An opinionated workflow for putting real money to work — written for someone deploying a modest book ($10K–$100K) against deep research, not for HFTs or fund managers.

This is the playbook the tool was built to support. Adapt it to your own risk tolerance and time horizon, but understand the *reasoning* before you change pieces of it.

---

## The premise

The edge is not stock-picking. The edge is:

1. **Asymmetric thesis structuring** — only entering positions where you can clearly state what would falsify the thesis, and exiting promptly when it does.
2. **Honest position sizing** — small bets when conviction is genuinely high; tiny bets when it isn't; no bets when the thesis is "vibes."
3. **Calibration accountability** — every recommendation is logged, every outcome is back-checked. You stop trusting your own gut and start trusting the parts of the process that actually work.

The tool exists to enforce all three.

---

## The daily routine

### Morning (10 minutes)

1. **Advisor** — read the overnight digest. Any DECAY signal severity ≥ medium on a position you hold? Read the signal summary; if it touches a "what would change my mind" criterion, the position is now actionable.
2. **Rebalance** — sort by `action` ≠ HOLD. For each non-HOLD row, click through to the source research and decide: act today, watch this week, ignore.
3. **Calibration** — once a week, check the hit rate by conviction band. If MEDIUM/HIGH calls are running below 50%, your sizing should drop until that recovers.

### Researching a new ticker (30–60 minutes)

1. **Deep Research v2** — let it run. Watch the SSE stream so you absorb the reasoning, not just the verdict.
2. **Read the Living Memo** end-to-end. Pay attention to open questions — those are gaps the tool itself flagged.
3. **Read the bull and bear cases**. If you can't articulate the bear case in your own words, you don't understand the position well enough to size it.
4. **Read the verdict + what would change my mind**. Is the falsifiability concrete? "Margins compress below 30%" is concrete. "Sentiment turns" is not.
5. **Decide your size** (see below).
6. **Enter the trade** with a stop at the verdict's recommended stop level. Don't widen it because you "feel" the position will work.

### Reviewing a held position (15 minutes, monthly per position)

1. **Re-run Deep Research v2** on the ticker. The Living Memo carries forward; the new run reads it and refines.
2. Compare the new verdict to your original entry thesis. Has anything material changed?
3. If conviction has dropped from HIGH to MEDIUM, consider trimming. If it's dropped to LOW, exit unless you have a non-tool reason to hold.
4. If "what would change my mind" has triggered, exit. No negotiation. (The whole point of falsifiability is to bind your future self.)

---

## Position sizing — the conservative rule

Until you've earned calibration data (see [Understanding the Outputs](understanding-outputs)), use this hard rule:

| Conviction | Max position size |
|---|---|
| HIGH | 8% of book |
| MEDIUM | 4% of book |
| LOW | 2% of book or skip |
| AVOID / SELL | 0% (and exit existing) |

These are caps, not targets. **A 4% MEDIUM position is normal; a 4% LOW position is aggressive.**

Once you have 20+ closed recommendations with outcomes, the **Calibration** page will start showing a real hit rate by conviction. You can scale these caps up by the ratio of (actual hit rate / 0.50) — i.e., if MEDIUM calls hit 65% over a real sample, you've earned the right to add 30% to MEDIUM sizing.

Do not scale up before you have the sample. A 10-call streak is not a calibration; it's variance.

---

## What to never do

- **Don't act on a single tool call.** The Verdict is the synthesis of bull + bear + judge + self-critique + macro + sector cohort. Cherry-picking one tool's output ignores the entire reason for the multi-agent design.
- **Don't override stops emotionally.** If you set a stop at $X and the position falls to $X, the position closes. Re-evaluate from neutral after the close, not from the position.
- **Don't add to losers without a re-run.** "Averaging down" is fine when the thesis is intact and the price is just noise; it's a wealth destroyer when the thesis is broken. A fresh Deep Research run on a -15% position is mandatory before adding.
- **Don't run on Ollama for positions you'll size up.** Local model verdicts are intentionally excluded from calibration. They're for exploration, not commitment.
- **Don't ignore the "what would change my mind" conditions.** If you do, you're using the tool as a vibes oracle instead of a research engine. Sell the tool back to yourself at that point.

---

## When to override the tool

You should override the tool when:

- You have **specific non-public knowledge** (you work in the industry, you know the team) that materially changes the thesis. Note it in the Living Memo so future-you can audit the decision.
- The **macro regime** has shifted in a way the tool's snapshot didn't capture (rate decision in the last hour, geopolitical event).
- **Tax or cash management** dictates the trade (year-end harvesting, liquidity need).

You should NOT override the tool when:

- The verdict feels wrong but you can't say *why* in one sentence.
- The position has gone up and you "want to take more risk."
- Friends/Twitter/Reddit are talking about the ticker.

A useful test: **write the override reason into the Living Memo before you trade.** If it's hard to write, it's probably hard to defend.

---

## What to read next

- [Understanding the Outputs](understanding-outputs) — calibration math, conviction calibration, why local-LLM runs aren't tracked.
- [Troubleshooting](troubleshooting) — for when something breaks.

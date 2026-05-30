# Edge Personal Markets Terminal (v3) — Power-User Guide

> A guide to using the Edge Personal Markets Terminal like an analyst, not a tourist.
> For the engineering spec, see [`next_gen_tool.md`](./next_gen_tool.md).

---

## What this is

Deep Research is the core decision-support engine of Portfolio Intelligence. Given a ticker, it runs a multi-source investigation, debates the thesis adversarially, distills what it learned into a per-ticker **Living Memo**, and produces a structured verdict with a concrete trade plan.

It is built on one premise: **a tool that helps you put real money to work has to earn your trust, not assume it.** Everything in this guide is in service of that.

---

## The terminal — navigation map

Edge is a pull-based terminal. Open it and you land on the **Terminal** — a daily
scan dashboard. Nothing fetches automatically beyond first paint, and nothing
runs the LLM on mount. Each panel has its own Refresh button; you pull when you
want fresh data.

Six pages, in the sidebar:

| Page | What it's for |
|---|---|
| **Terminal** | Daily scan. Movers (top gainers/losers across your watchlist ∪ the theme universe), Theme Heat (per-theme median move with leader/laggard), Watchlist (with day change), Hypotheses (on-demand AI "why" per ticker), Fresh Catalysts (next 7 days), a News Tape, and a Flow snapshot (degrades cleanly without an Unusual Whales key). |
| **Stock View** | Single-ticker cockpit. Click any ticker — in Movers, Watchlist, the News Tape, Theme Heat, or Catalysts — to open it. Price header, candlestick chart with MA/Bollinger/VWAP overlay toggles and multiple ranges, key fundamentals, ownership & insider activity, a merged filings/news timeline, theme-pack context, and a CTA bar that deep-links into the Console. |
| **Console** | The on-demand brain. Type a slash command to kick off analysis: `/thesis <T>` (full report), `/dossier <T>` (deep dive), `/why <T>` (cheap 3-sentence read), `/theme <slug>` (theme-level verdict), `/compare <A> <B> <C>` (ranking + head-to-head). Everything streams live. |
| **Library** | Your saved reports and Living Memos. |
| **Screener** | Rule-based screening over cached tool data. Build rules like "RSI < 30 AND yoy_revenue_growth > 0.20" over a theme/watchlist universe; matched tickers link straight to Stock View. Save configs for reuse. |
| **Settings** | LLM provider and keys; data-tier badges (which paid feeds are live, detected from env); and the themes editor (create/delete theme packs, add/remove tickers). |

The flow is: **scan on the Terminal → click into a Stock View → run a command in
the Console.** The Console's "Run thesis" button on a Stock View pre-fills the
command so you go from "this looks interesting" to a streaming report in two
clicks.

### Running a command

On the Console, type `/thesis NVDA` and press Run (or click "Run thesis" from any
Stock View). The stream shows the sector classification, each tool call as it
completes, the Bull and Bear arguments, and the Judge's verdict — the same v2
deep-research engine described below, now driven from a command bar. `/dossier`
is the same with a deeper budget. `/theme ai-infra` runs the debate over a whole
theme pack and returns a theme-level verdict. `/compare NVDA AMD AVGO` runs a
quick pass on each name in parallel, then ranks them head-to-head.

### Theme packs

The Terminal scans a universe defined by **theme packs** — named cohorts of
tickers (e.g. `ai-infra`, `hbm-memory`, `dc-power`). A default AI/semis-pilled
pack seeds on first boot; edit it in Settings. Theme Heat ranks each pack by its
constituents' median move and surfaces the day's leader and laggard, so you can
see which corner of the market is in play before you drill in.

### Hypotheses — cheap reads, on demand

The Hypotheses panel never spends on mount. Click **Generate** next to a
watchlist ticker and the `/why` path runs: it pulls news, financial trends,
technicals, and sentiment, makes a single LLM call, and returns three cited
sentences explaining the move plus what to watch next. Each generation is
~$0.05 and cached for 4 hours, so re-opening is free. This is the fast triage
step before committing to a full `/thesis`.

---

## Philosophy — read this first

### 1. The tool reasons; you decide.
The Verdict is a *hypothesis with explicit falsifiability*, not a recommendation. The system tells you what would change its mind. You decide whether the case is strong enough for *your* capital, your time horizon, your risk tolerance.

### 2. Distillation over retrieval.
Most "AI research" tools dump raw documents at you or chunk-retrieve them on demand (RAG). Deep Research does the opposite: it maintains a **Living Memo** per ticker — a curated, evolving expert file that gets refined every session. Your 50th research on NVDA is genuinely deeper than your first, because each run reads the prior memo, identifies what's stale or unresolved, investigates that, and writes a more refined version. The raw data is fetched on demand by tools; the *understanding* compounds in the memo.

### 3. Every claim cites its source.
There are no naked numbers. Every figure in a report has a click-through to the tool that produced it, the timestamp, and a confidence rating. If a claim has no citation, it's an LLM hallucination — flag it.

### 4. Calibration is the trust loop.
Every recommendation the tool makes is logged with the price at the time, your stop, your targets, and the falsifiability conditions. A nightly job tracks what actually happened at 1m / 3m / 6m / 1y. Over months you see the tool's real hit rate by conviction level and by sector. **Don't trust the tool. Watch its calibration and let trust accumulate or evaporate based on outcomes.**

### 5. More data ≠ better decisions.
The hardest problems in investing are *sizing, taxes, and behavior*, not stock-picking. Deep Research can compress information access. It cannot fix sizing discipline or stop you from panic-selling. The tool is the easy part.

---

## The Living Memo — your compounding edge

This is the most important concept in v2.

### What it is
A versioned markdown document per ticker, organized into 10 sections:

| Section | What it tracks |
|---|---|
| **Identity** | Business model, segments, geographies. Slow-changing. |
| **Moat** | Competitive durability, evidence, trajectory (expanding / eroding) |
| **Long-term thesis** | The secular drivers we believe in, with evidence |
| **Current state** | Latest fundamentals snapshot, valuation context |
| **Management track record** | Guidance promised vs delivered, quarter by quarter |
| **Risk register** | Known risks × {severity, probability, mitigant, monitoring trigger} |
| **Open questions** | What we don't know; what to watch for |
| **Recent observations** | Timeline of notable events with our interpretation |
| **Past verdicts** | Every recommendation we've made + outcome (calibration) |
| **Anti-thesis** | The strongest bear case we acknowledge as legitimate |

### How it works
1. You hit "Deep Research" on NVDA.
2. The agent loads the existing NVDA memo (if any).
3. The **Planner** reads the memo's *Open Questions* and *Risk Register* and decides what to investigate this session — *not* a fixed checklist.
4. Tools run. Evidence accumulates. Bull, Bear, Judge debate.
5. The **Memo Synthesizer** proposes a diff: red strikethroughs for falsified claims, green for newly confirmed, italic for newly uncertain.
6. You review the diff. Accept, edit individual sections, or reject.
7. The accepted memo becomes the new version. Prior versions retained forever.

### Why this is better than RAG
- **Coherent narrative, not chunks.** Reasoning happens over compressed understanding, not retrieved snippets.
- **Compounds over time.** Each session leaves the memo smarter.
- **Auditable.** You can read, edit, override. RAG gives you a vector store you can't reason about.
- **Cheap to load.** A 5-page memo is a few thousand tokens. RAG of 4 quarters of filings is hundreds of thousands.
- **Catches drift.** *"3 months ago we thought margins were durable; now we're seeing X — does the moat assessment need updating?"* Memo makes this visible.

### Practical workflow
- **First research on a ticker**: memo bootstraps from scratch. Spend a few minutes reviewing the initial proposal — this becomes your foundation.
- **Recurring research (weekly / post-earnings)**: skim the diff. Five minutes if nothing material; longer if the diff is large.
- **Manual edits**: any time you read something elsewhere that changes your view, edit the memo directly. The agent respects your edits on the next pass.
- **Version diffing**: when conviction changes, look at memo v3 vs v8 to see *why* the thesis evolved.

---

## Anatomy of a Deep Research run

A v2 run streams these events live:

```
1.  Bootstrap         — load Living Memo, classify sector
2.  Planner round 1   — propose initial tool calls
3.  Tool calls        — fundamentals, transcripts, insider, macro, ...
                        (run in parallel where possible; each emits SSE)
4.  Observer          — evidence aggregated; planner replans
5.  Tool calls        — round 2 (and possibly 3, 4...)
6.  Bull agent        — builds strongest bull case from evidence only
7.  Bear agent        — attacks bull case + builds independent bear case
8.  Judge agent       — weighs both; emits structured verdict + falsifiability
9.  Self-critique     — attacks the verdict; may trigger another planner round
10. Memo synthesis    — proposes diff to Living Memo
11. Trade planner     — translates verdict into entry / stop / targets / size
12. Done              — full report assembled
```

Total wall time: **20-60 seconds** depending on budget profile and how many tool rounds the planner triggers.

You can watch every step live in the UI. The "Research Log" tab shows the full audit trail with every tool call, args, latency, and cost.

---

## Reading the verdict

The Judge agent's output:

```json
{
  "summary": "One-sentence verdict",
  "recommendation": "BUY | HOLD | TRIM | AVOID",
  "conviction": "HIGH | MEDIUM | LOW",
  "bull_case": [{ "claim", "evidence_refs", "confidence" }, ...],
  "bear_case": [{ "claim", "evidence_refs", "confidence" }, ...],
  "what_would_change_mind": [
    "If quarterly revenue growth drops below 15% for 2 consecutive quarters",
    "If insider selling exceeds insider buying by 3:1 over a quarter",
    "If gross margin compresses below 65%"
  ],
  "key_catalysts": [
    { "event", "date", "expected_impact" }
  ],
  "target_price_range": { "low", "high", "timeframe" },
  "trade_plan": {
    "entry_zone": { "lower", "upper", "logic" },
    "stop_methodology": "1.5x ATR below 50DMA / specific support / etc.",
    "targets": [{ "price", "size_to_take_off_pct" }],
    "time_stop": "If thesis hasn't moved by X date, reassess",
    "position_size_pct": "...",
    "rationale": "..."
  }
}
```

### How to actually read this
- **Read `what_would_change_mind` first.** It tells you the *falsifiability conditions*. If you can't imagine any of them happening, the thesis is too easy. If they all sound likely, the thesis is too fragile.
- **Then read the bear case.** Specifically check: did the Bear agent cite different evidence than the Bull, or did they argue over the same facts? Differing-evidence debates are healthier than same-evidence interpretations.
- **Then the bull case.** With the bear's attacks in mind.
- **`summary` and `recommendation` last.** These compress a lot of reasoning; treat them as table-of-contents, not conclusions.

### Conviction levels — what they actually mean
- **HIGH**: thesis has multiple independent supports; bear case has been addressed with evidence; falsifiability conditions are clearly defined and currently distant.
- **MEDIUM**: thesis is reasonable but one or more bear arguments remain partially unresolved; or evidence is missing in a key area.
- **LOW**: significant unresolved questions; the verdict is a flag for more research, not a basis for sizing.

**Recommendation: don't size HIGH-conviction calls until your personal calibration log shows the tool has earned that level on past calls.** Start small. Let the data accumulate.

---

## Reading citations

Every datum in a report has a source. Click any number to see:
- Which tool produced it (`transcripts`, `fundamentals`, `insider_form4`, ...)
- When it was fetched
- Underlying URL if applicable (SEC filing link, news headline, transcript paragraph)
- Confidence rating

**Red flags**:
- A claim with `confidence: low` being cited in a HIGH-conviction thesis
- A claim whose source is `llm_inferred` (means the model derived it rather than fetched it — should be rare; flag if seen)
- A specific number that has no source citation at all

---

## Tools and what they're for

| Tool | Use it when |
|---|---|
| `fundamentals` | Always. Baseline financial snapshot. |
| `financial_trends` | Always. 8-12 quarter trajectory — does the business accelerate or decelerate? |
| `technicals` | Entry timing, not thesis. RSI/MACD/MAs/pattern detection. |
| `dcf_valuation` | Valuation context: cheap, fair, or rich? Three scenarios. |
| `peer_compare` | Relative valuation; is the multiple deserved? |
| `transcripts` | Tone shifts, guidance walks, management credibility. Best leading indicator. |
| `insider_form4` | Clustered exec buying = strong bull signal. CEO dumping = caution. |
| `institutional_13f` | Smart-money positioning. Look at Q/Q delta, not absolute holdings. |
| `options_flow` | Real institutional positioning + entry timing (high IV → sell premium, don't buy calls). |
| `qoe_forensics` | Beneish/Altman/Piotroski/accruals — catches financial engineering. Always for unfamiliar names. |
| `macro_context` | Risk-on or risk-off regime? Same stock behaves differently. |
| `alt_data` | Leading indicators: hiring trends, web traffic, app rank, search interest. |
| `catalyst_lookup` | What's coming up that could move the price? |
| `sentiment` | Background context. Use *extreme* sentiment as contrarian signal. |
| `edgar_filings` | Deep dive on a specific section: risk factors, MD&A, segment data. |

You don't choose tools manually — the **Planner** decides based on what the Living Memo says you don't yet know. But understanding what each does helps you read the Research Log and judge whether the right tools ran.

---

## Sector specialization

Different sectors get different KPI templates and peer cohorts:

| Sector | Sector-specific KPIs |
|---|---|
| **SaaS** | ARR, NRR, Rule of 40, magic number, CAC payback, gross retention |
| **Banks** | NIM, efficiency ratio, NPL ratio, deposit beta, Tier 1 capital, ROTCE |
| **REITs** | FFO, AFFO, occupancy, WALT, cap rate vs treasury spread, lease ladder |
| **Biotech** | Pipeline (Phase 1/2/3), PDUFA dates, cash runway, trial readouts |
| **Energy** | Reserves, breakeven price, production growth, F&D costs, hedging |
| **Semis** | Wafer pricing, capex cycle position, customer concentration, lead times |
| **Consumer** | Comp store sales, inventory turn, gross margin spread, brand strength |

The sector is detected automatically from GICS sub-industry, with LLM fallback for edge cases. You can override the classification if it gets it wrong.

---

## The trade plan

Every verdict ends in a trade plan with five fields:

### Entry zone
A price range, not a single price. The rationale explains *why* this range — e.g., "20-DMA + 1 ATR pullback gives 3 ATR to stop loss while target offers 7 ATR upside."

### Stop methodology
Three styles supported:
- **Volatility stop**: N × ATR below entry (default 1.5x)
- **Structure stop**: below a specific named support level (e.g., "below 200-DMA")
- **Thesis stop**: triggered by a `what_would_change_mind` condition, not price

The default is volatility-based. Override in the Trade Plan section.

### Targets (scaled)
Usually multiple targets with `size_to_take_off_pct` at each. Standard pattern: 50% off at 1R (initial risk), 25% at 2R, runner with trailing stop.

### Time stop
"If thesis hasn't started playing out by [date], reassess." Prevents thesis drift — you bought it for a reason, that reason has a timeline.

### Position size
Computed via Half-Kelly with portfolio-level vol budget and per-position caps. Specific dollar amount given your portfolio value. **Use this as a ceiling, not a floor.** Until calibration earns trust, size at 25-50% of the recommendation.

---

## Calibration — the trust loop

> **Not in v3.** The Calibration Dashboard and its nightly background job were removed — Edge is pull-based (no cron/workers). Recommendations are still logged when you run `/thesis` or `/dossier`, but outcome tracking is not automated. Treat the section below as the original design intent, not current behavior.

The Calibration Dashboard answers one question: **"how often is this tool actually right?"**

Updated nightly by a background job that tracks every recommendation's outcome at 1m / 3m / 6m / 1y horizons.

Metrics shown:
- **Hit rate by conviction** — HIGH calls should have meaningfully higher hit rates than LOW. If they don't, conviction labels are meaningless.
- **Hit rate by sector** — the tool may be great at semis, mediocre at biotech.
- **Avg return vs benchmark (SPY)** — alpha, not just absolute returns.
- **Brier score** — calibration quality. Lower is better. 0 = perfect.
- **Worst losses + post-mortems** — what went wrong, why, what the memo should have caught.

**How to use it**: don't trust HIGH conviction until the dashboard shows HIGH calls have meaningfully higher hit rates than MEDIUM over ≥30 calls. Until then, size conservatively.

This dashboard is also the post-mortem engine. When a recommendation fails, the system surfaces:
- What the memo said vs what happened
- Which `what_would_change_mind` condition triggered (if any)
- What evidence was available at decision time that the agent missed

That's how the tool — and you — get smarter.

---

## Conversational follow-up

After a research session, you can chat with the report. The LLM has:
- The full report
- The Living Memo
- Access to every tool (it can fetch more data mid-conversation)

**Good questions to ask**:
- *"Why do you think margins will compress?"* → cites specific transcript paragraphs
- *"What if Fed cuts to 3% next year?"* → reruns DCF with new discount rate
- *"How does this compare to AMD on the same metrics?"* → calls competitor_compare
- *"What's the strongest argument I'd hear from a skeptic in person?"* → rerun bear agent with more aggressive prompt
- *"Show me the management track record on revenue guidance."* → calls transcripts with guidance-walk filter

**Bad questions**:
- *"Should I buy?"* — already answered in the verdict; rephrase as "what would have to change for you to recommend BUY?"
- *"What will the stock do tomorrow?"* — the tool doesn't predict prices; it assesses theses.

---

## Configuration

### Budget profiles
Set in LLM Settings:

| Profile | Cost / research | What it does |
|---|---|---|
| **Quick** (~$0.10) | Fundamentals + sentiment + cached memo read only. For watchlist scanning. |
| **Normal** (~$0.60) | Full v2 default. Use for any name you're considering for capital. |
| **Deep** (~$2.00) | Extra transcript dives, additional debate rounds, longer planner horizon. Use for new positions and post-earnings reassessments. |

### LLM provider
Recommended for v2:
- **Claude Sonnet 4.6** — best balance of cost + reasoning quality. Default.
- **Claude Opus 4.7** — best reasoning. 5x cost. Use for Deep profile only.
- **Gemini 2.5 Pro** — viable alternative, lower cost.
- **Ollama (local)** — only viable for Quick profile; reasoning quality on debate is materially lower.

### Caching
- Living Memo cached forever (versioned)
- Transcripts cached per quarter (until next earnings)
- Insider trades cached for 24h
- 13F cached until next quarterly filing
- Options metrics cached for 4h
- Fundamentals cached for 4h
- Macro context cached for 1h

Force a fresh run with the "Refresh" button or `?refresh=true` query param.

### Active monitoring

> **Not in v3.** There is no monitoring worker, daily digest, or notifications — Edge is pull-based. To re-check a position, open its Stock View or run `/why <T>` / `/thesis <T>` in the Console. The design below is historical.

For any owned position, toggle "Monitor" to enable the daily digest. The monitoring worker:
1. Reruns cheap tools each day (price action, new filings, insider, news)
2. Compares against the last Living Memo
3. Flags material changes in a daily digest
4. Triggers notifications when a `what_would_change_mind` condition is breached

---

## Worked example: a session on NVDA

You research NVDA for the first time.

1. **Bootstrap**: empty memo. Planner identifies all sections as `unknown`.
2. **Round 1 tools**: `fundamentals`, `financial_trends`, `technicals`, `sentiment`, `macro_context` — run in parallel.
3. **Round 2**: planner sees high valuation + concentrated customer base → fires `transcripts` (last 8 quarters), `institutional_13f`, `qoe_forensics`.
4. **Round 3**: transcripts surface heavy hyperscaler dependency. Planner fires `competitor_compare` against MSFT/META capex trends to assess customer demand sustainability.
5. **Debate**:
   - Bull cites: revenue growth 122% YoY (`financial_trends`), gross margin 75% (`fundamentals`), hyperscaler capex guides up 40%+ (`competitor_compare`), insider buying cluster Q1 (`insider_form4`).
   - Bear attacks: gross margin only sustainable if no real competition emerges (no evidence yet for or against); customer concentration top-4 = 60% (transcripts); valuation 42x fwd P/E vs sector 28x (peer_compare); QoE shows accelerating SBC dilution (`qoe_forensics`).
   - Judge: recommendation BUY, conviction MEDIUM. Falsifiability: *"if any of top-4 hyperscalers signals capex deceleration"*, *"if gross margin drops below 70% in any quarter"*, *"if insider selling exceeds buying 2:1 for 2 quarters"*.
6. **Memo synth**: proposes a full first draft of all 10 sections.
7. **Trade plan**: entry $850-875, stop $792 (1.5x ATR + below 50DMA), targets $980 (50%) / $1100 (25%) / runner, time stop 90 days, size 4% of $10K portfolio = $400.

You skim the diff, accept with one edit (you don't believe the moat is as durable as proposed; downgrade *Moat → "moderate, evidence mixed"*). Memo v1 saved.

Three weeks later, post-earnings, you research NVDA again. The planner now sees the memo's specific Open Questions (*"is gross margin sustainable?", "is hyperscaler capex still growing?"*) and runs targeted tools. Round 1 fetches the new transcript + latest financials. The Bear agent flags that gross margin came in at 73% (still above 70% trigger), but management guided next quarter to 71% — moving toward your falsifiability line. Judge downgrades conviction to LOW until next print. Memo v2 records this; recommendations table updates the original BUY's `outcome_thesis_falsified = 0` (not yet).

Six months later, a price drop triggers your stop. Calibration log records the loss. Post-mortem: "Bear case correctly identified margin pressure; Judge gave MEDIUM conviction which was appropriate given evidence; trade plan stop worked as designed. Net: thesis was partially wrong but risk-managed correctly."

This is the loop.

---

## Anti-patterns — don't do these

**Trusting HIGH conviction without calibration history.** No tool earns trust by claiming it; only by track record. Until your Calibration Dashboard shows differentiated outcomes by conviction over ≥30 calls, ignore the conviction label and size everything at MEDIUM-equivalent.

**Sizing off the recommended position size on day one.** Recommended size assumes the tool's calibration is real. Halve or quarter it until proven.

**Ignoring `what_would_change_mind`.** If you can't tell me the conditions that would invalidate the thesis, you don't own the thesis — the model does.

**Re-researching after every price move.** Price action ≠ thesis change. If your falsifiability conditions haven't triggered, the thesis is intact. Re-research after material news, earnings, or trigger conditions — not after a 5% pullback.

**Editing the memo to match what you wish were true.** The memo is your map. If you edit it to look better than reality, you'll get lost.

**Conversational follow-up without checking sources.** The chat agent can hallucinate. Click citations on critical claims, especially when the chat goes beyond what the original report contained.

**Treating sentiment as confirmation.** WSB bullish at extreme = contrarian sell signal historically. Sentiment is context, not signal.

**Skipping the Bear case.** Reading only the bull case is how people lose money. The Bear is the most important agent.

---

## When NOT to trust Deep Research

Be skeptical when:
- **Pre-revenue or pre-product names** — fundamentals/trends tools have nothing to chew on; the thesis is mostly narrative.
- **M&A pending** — price reflects deal probability, not fundamentals.
- **Liquidity-driven moves** (short squeezes, gamma squeezes) — the technicals/options tools may show signal but the move is mechanical.
- **Macro regime changes** — tool conviction at extremes (HIGH BUY during rate-hike cycles in unprofitable growth names) is suspect.
- **First research on a sector you don't understand** — even with sector specialization, you'll struggle to evaluate the verdict critically.

When skeptical, default to **read the debate transcript directly** rather than acting on the verdict. The debate is the unfiltered reasoning.

---

## Quick reference

| You want to | Do this |
|---|---|
| Research a new ticker | Console → `/thesis <T>` (normal budget) |
| Quick "why is it moving" read | Console → `/why <T>` (or the Terminal Hypotheses panel) |
| Post-earnings deep dive | Console → `/dossier <T>` (deep budget) |
| Compare several names | Console → `/compare <A> <B> <C>` |
| Map a theme | Console → `/theme <slug>` |
| Scan for setups | Screener → build/run a rule |
| Understand why conviction changed | Library → Memo version diff |
| Find a specific historical claim | Library → Memo section |
| Audit a number | Click the citation chip |
| Override a sector classification | Memo → Identity section → edit |

---

## Further reading

- [`next_gen_tool.md`](./next_gen_tool.md) — engineering architecture, DB schema, API endpoints, tool registry internals
- Source code: `analysis/agent_loop.py`, `analysis/living_memo.py`, `analysis/agents/`, `analysis/tools/`

If something in this guide doesn't match what the tool does, the tool is the source of truth. File an issue or update the guide.

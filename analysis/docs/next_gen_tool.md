# Portfolio Intelligence — Architecture & Specification

> **Status**: v1.0 shipped · v2.0 "Living Analyst" in design
> **Last updated**: 2026-05-17
> **Audience**: Engineers and contributors. For a power-user guide to Deep Research, see [`deep_research_guide.md`](./deep_research_guide.md).

---

## 0. Document map

This spec is split into two parts:

- **Part I — Foundation (v1.0)**: what's shipped today. The 8-stage pipeline, Robinhood ingestion, alerts daemon, S&P 500 scanner.
- **Part II — Living Analyst (v2.0)**: the in-design upgrade. Tool-based agent loop, per-ticker Living Memo, multi-agent debate, citation infrastructure, sector specialization, personalization, calibration.

v2.0 is *additive* — v1 endpoints stay; v2 adds a parallel `/api/research/<ticker>/v2/stream` and a new memo/chat/calibration surface. Migration is opt-in per UI toggle until v2 is the default.

---

# Part I — Foundation (v1.0, shipped)

## 1. Vision

The original tool was a passive S&P 500 viewer. v1 bridged that gap: it connects to a real portfolio (Robinhood or manual), runs multi-layer AI research on any US ticker, and produces a structured investment thesis with concrete actions. Think Bloomberg Terminal × ChatGPT, single-investor scale.

## 2. Shipped capabilities

### 2.1 Portfolio ingestion
- **Robinhood**: OAuth + OTP via `robin_stocks` (unofficial). Session cached 24h in `.cache/rh_session.json` (no password stored).
- **Manual CSV**: `ticker,shares,avg_cost` parsing.
- **Live enrichment**: `yfinance` for current prices, P&L, weights.

### 2.2 Deep Research pipeline (v1)
8 fixed stages, streamed via SSE:

| Stage | Source | Output |
|---|---|---|
| Fundamentals | yfinance `.info` | P/E, margins, growth, balance sheet |
| Financial trends | yfinance quarterly | 8-12 quarter trajectory + signals |
| Valuation | computed | DCF base/bull/bear + peer comp |
| Technicals | yfinance prices | RSI, MACD, BB, MAs, 11 patterns |
| Risk management | computed | Half-Kelly sizing, stop, target |
| Sentiment | Finnhub + Reddit (praw) + yfinance | Weighted composite score |
| EDGAR | SEC | 10-K/10-Q sections, LLM-summarized |
| Thesis | LLM | 3-pass bull → bear → synthesis JSON |

### 2.3 Portfolio rebalancing
Risk-profile-driven allocation analysis (Conservative / Moderate / Aggressive) → prioritized trim/add actions.

### 2.4 Watchlist + alerts
Watchlist: notes + one-click research. Alerts: daemon thread (`alert_worker.py`) polls every 60s for `above | below | change_pct_up | change_pct_down` triggers.

### 2.5 S&P 500 scanner (legacy)
Sector tables, market stats, technical pattern hunting, spotlight categories.

## 3. v1 Architecture

```
┌─────────── UI (React 18 SPA, Vite) ───────────────────┐
│ Sidebar → 8 lazy pages                                │
└────────────────────────┬──────────────────────────────┘
                         │ REST + SSE
┌────────────────────────▼──────────────────────────────┐
│           Flask backend (app.py, 43 routes)           │
│                                                       │
│  research_stream.py  ── 8-stage SSE pipeline          │
│  research_engine.py  ── stage implementations         │
│  portfolio_service   ── Robinhood / CSV / P&L         │
│  sentiment_service   ── Finnhub + Reddit + yf         │
│  edgar_service       ── SEC 10-K/10-Q                 │
│  llm_service         ── Claude / Gemini / Ollama      │
│  rebalancing_engine  ── allocation analysis           │
│  alert_worker        ── daemon, 60s poll              │
│  db.py               ── SQLite (WAL)                  │
└───────────────────────────────────────────────────────┘
```

## 4. v1 Data sources

| Source | Data | Cost |
|---|---|---|
| `robin_stocks` | holdings | free |
| `yfinance` | prices, fundamentals, quarterly | free |
| Finnhub | news, analyst ratings | free tier |
| `praw` (Reddit) | WSB + r/investing | free tier |
| SEC EDGAR | 10-K / 10-Q | free |
| LLM (Claude / Gemini / Ollama) | synthesis | provider-dependent |

## 5. v1 Endpoints (research surface)

| Endpoint | Notes |
|---|---|
| `GET /api/research/<ticker>` | Full report (cached 24h) |
| `GET /api/research/<ticker>/stream` | SSE — 8 stages |
| `GET /api/research/<ticker>/thesis` | Cached thesis only |
| `POST /api/research/compare` | 2-4 ticker side-by-side |
| `GET /api/research/sector/<sector>` | Sector summary |
| `GET /api/research/etf/<ticker>` | ETF-aware (skips EDGAR) |

## 6. v1 DB schema

```
portfolio_holdings  (id, ticker, shares, avg_cost, source, synced_at)
watchlist           (id, ticker, added_at, notes)
alerts              (id, ticker, condition, threshold, is_active, is_triggered, triggered_at, created_at)
research_cache      (id, ticker UNIQUE, report_json, llm_provider, generated_at)
research_reports    (id UUID, ticker, full JSON, llm_conversations, generated_at)
llm_settings        (id singleton, provider, model_fast, model_deep, api_key, base_url)
```

## 7. v1 LLM design

User configures provider + fast/deep model pair. Routing in `llm_service.py`:
- `task='sentiment'` → fast model
- `task='thesis' | 'edgar'` → deep model

Thesis output strict JSON:
```json
{ "summary", "bull_case", "bear_case", "key_catalysts",
  "recommendation": "BUY|HOLD|TRIM|AVOID",
  "conviction": "HIGH|MEDIUM|LOW",
  "target_price_range": {...},
  "action_items": [...] }
```

The existing 3-pass implementation in `research_stream.py` already runs bull-draft → bear-attack → synthesizer. v2 formalizes and extends this.

---

# Part II — Living Analyst (v2.0, in design)

## 8. Motivation: what v1 cannot do

v1 is a **report generator**. v2 is a **research analyst**. Three structural gaps drive v2:

1. **Fixed pipeline ≠ adaptive investigation.** v1 runs the same 8 stages whether the ticker is a pre-revenue biotech, a regional bank, or a hyperscaler. A real analyst chooses what to investigate based on the question.

2. **Stateless ≠ compounding knowledge.** v1 starts fresh every call. A real analyst maintains an evolving file on each name — what we've learned, what management has promised vs delivered, what's still unknown.

3. **Single-pass thesis ≠ adversarial reasoning.** v1's 3-pass bull/bear/synth is a good start but bull-evidence and bear-evidence are not separately *cited* and there is no falsifiability check.

v2 addresses all three.

## 9. Design principles

1. **Tools first.** Every data fetch is a Tool with citation metadata. The LLM has no privileged access — it sees only what tools return.
2. **Distill, don't retrieve.** The Living Memo is the long-term store. Raw documents only enter when a Tool fetches a specific span on demand.
3. **Debate, don't single-shot.** Bull, Bear, Judge run as separate agents with separate prompts and separate evidence threads.
4. **Cite everything.** No claim without a source. Frontend renders citations as click-throughs.
5. **Calibrate, then trust.** Every recommendation is logged with price/date; outcomes auto-tracked. Trust is earned, not asserted.
6. **Stream progressively.** Even an agentic loop emits SSE per tool call so the UI feels live.
7. **Additive, not destructive.** v1 endpoints unchanged; v2 lives in parallel until proven.

## 10. v2 architecture overview

```
┌──── UI: Deep Research v2 ─────────────────────────────────────┐
│  Live stream │ Memo viewer │ Source viewer │ Chat │ Calib.    │
└───────────────────────────────┬───────────────────────────────┘
                                │ SSE + REST
┌───────────────────────────────▼───────────────────────────────┐
│                      Agent Loop (agent_loop.py)               │
│                                                               │
│   load_memo → planner → tool_executor → observer ──┐          │
│        ▲                                            │          │
│        └──── re-plan until done or budget hit ─────┘          │
│                                                               │
│   → bull_agent  ─┐                                            │
│   → bear_agent  ─┼─→ judge_agent ─→ self_critique ─→ memo_synth│
│   → evidence    ─┘                                            │
└───────────────────────────────┬───────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   ┌─────────┐           ┌─────────┐             ┌──────────┐
   │  Tools  │           │ Memory  │             │  Output  │
   │registry │           │         │             │          │
   └────┬────┘           └────┬────┘             └────┬─────┘
        │                     │                       │
  fundamentals          living_memo            recommendations
  transcripts           memo_versions          trade_plans
  insider_form4         tool_call_log          catalysts
  institutional_13f
  options_flow
  qoe_forensics
  macro_context
  alt_data
  edgar_filings
  peer_compare
  correlation_w_portfolio
  catalyst_lookup
  ...
```

## 11. The Agent Loop

`analysis/agent_loop.py` runs a budget-bounded loop:

```python
def run_deep_research(ticker, user_portfolio, budget):
    memo = LivingMemo.load(ticker)              # may be empty
    sector_profile = SectorRouter.classify(ticker)
    evidence = EvidenceLedger()                 # citation-tagged store

    plan = Planner.initial_plan(ticker, memo, sector_profile, user_portfolio)

    while not plan.done and budget.remaining():
        results = ToolExecutor.run_parallel(plan.next_calls, budget)
        evidence.add_all(results)              # each carries source + confidence
        plan = Planner.replan(memo, evidence, plan)

    bull = BullAgent.argue(evidence)            # cites only from evidence
    bear = BearAgent.argue(evidence)
    verdict = Judge.synthesize(bull, bear, evidence)
    verdict = SelfCritique.attack(verdict, evidence)

    memo_delta = MemoSynthesizer.diff(memo, evidence, verdict)
    trade_plan = TradePlanner.from_verdict(verdict, user_portfolio)

    return Report(memo_delta, verdict, trade_plan, evidence, audit_log)
```

**Budget** — a dollar amount and a wall-clock limit. The planner gets `budget.remaining()` and chooses tools accordingly. A `quick` profile may spend $0.10; a `deep` profile up to $2.

**Planner prompt** — receives: (a) memo's *Open Questions* section, (b) sector profile's required KPIs, (c) evidence gathered so far, (d) user portfolio context. Returns a JSON plan: `{next_calls: [{tool, args, reason}], done: bool, confidence: float}`.

## 12. Tool registry

Each tool lives in `analysis/tools/<name>.py` and implements:

```python
class Tool:
    name: str
    description: str                # for LLM tool-use schemas
    cost_estimate: Callable[[args], float]    # USD
    schema: dict                    # JSON schema for args
    cache_policy: CachePolicy       # TTL or content-hash

    def execute(self, **args) -> ToolResult: ...

@dataclass
class ToolResult:
    data: dict
    sources: list[Source]           # {tool, field, url?, fetched_at}
    confidence: Literal['high','medium','low']
    cost_actual: float
    latency_ms: int
```

### 12.1 Existing-data tools (refactored from v1)

| Tool | Replaces | Notes |
|---|---|---|
| `fundamentals` | `fetch_fundamentals` | yfinance `.info` |
| `financial_trends` | `fetch_financial_trends` | quarterly trajectory |
| `technicals` | `fetch_technicals` | RSI/MACD/BB/MA/patterns |
| `dcf_valuation` | `compute_intrinsic_value` | base/bull/bear |
| `peer_compare` | `get_peer_valuation` | extended with real peers (v1 mocks) |
| `sentiment` | `sentiment_service` | Finnhub + Reddit + yf |
| `edgar_filings` | `edgar_service` | now per-section retrieval, not full summary |

### 12.2 New data-depth tools

| Tool | What it pulls | Source | Why it matters |
|---|---|---|---|
| `transcripts` | last 8 earnings call transcripts; guidance walk; KPI mention cadence | Financial Modeling Prep API or Seeking Alpha scrape | Tone shifts predict numbers; guidance track record assesses mgmt credibility |
| `insider_form4` | SEC Form 4: exec buys/sells with role, $ amount, % of holdings | SEC EDGAR Form 4 RSS + XBRL | Clustered insider buying is strongest single bullish signal in lit |
| `institutional_13f` | quarterly holdings of named institutions (Berkshire, Citadel, Druckenmiller, etc.); Q/Q delta | SEC EDGAR 13F-HR | Smart-money positioning, conviction sizing |
| `options_flow` | IV rank, IV percentile, P/C ratio, skew, unusual blocks | Tradier API (free dev tier) or yfinance `.option_chain` | Real positioning data; entry-timing |
| `qoe_forensics` | Beneish M-score, Altman Z, Piotroski F, accrual ratio, SBC/revenue, DSO trend | computed from existing financials | Catches earnings manipulation, bankruptcy risk, low quality |
| `macro_context` | yield curve slope, DXY, VIX term structure, HY credit spreads, sector RS, breadth | FRED API + yfinance | Same stock, different macro = different bet |
| `alt_data` | Google Trends product searches, LinkedIn job postings delta, Glassdoor sentiment trend, app rank | pytrends + scrapers/APIs | Cheap leading indicators |
| `catalyst_lookup` | upcoming earnings, FDA PDUFA, FOMC, OPEC, lockup expiries, conferences | yfinance + RSS feeds | Don't get blindsided / time entries |
| `competitor_compare` | peer financials in same trend window, ranked on each KPI | yfinance + sector cohort | Relative strength is what matters |
| `news_timeline` | recent news events annotated on price chart with causality scoring | Finnhub + LLM tagger | Separates real catalysts from noise |

### 12.3 Decision tools

| Tool | What |
|---|---|
| `position_sizing` | extends v1's `compute_position_sizing` with portfolio-level vol budget + concentration caps |
| `correlation_analysis` | correlation with user's existing holdings, factor overlap |
| `stress_test` | historical scenario performance: '08, COVID, '22 rate shock, dot-com |

### 12.4 Meta tools

| Tool | What |
|---|---|
| `memo_read` | fetch current Living Memo for a ticker |
| `memo_section_read` | fetch a specific memo section |
| `calibration_lookup` | this tool's past calls on this ticker + outcomes |
| `sector_peers_lookup` | sector-specific peer cohort |

## 13. The Living Memo

**File**: `analysis/living_memo.py`
**Storage**: `living_memo` and `living_memo_versions` tables.

A Living Memo is the agent's persistent knowledge of one ticker. It is stored as both human-readable markdown and structured JSON for programmatic access.

### 13.1 Sections

| Section | Purpose | Updated by |
|---|---|---|
| `identity` | Business model, segments, geographies | Rare changes |
| `moat` | Competitive durability, evidence, trajectory | Every research |
| `long_term_thesis` | Secular drivers we believe / don't believe | When verdict shifts |
| `current_state` | Latest fundamentals snapshot, valuation context | Every research |
| `management_track_record` | Guidance promised vs delivered, hit rate over N quarters | Quarterly (after earnings) |
| `risk_register` | Known risks × {severity, probability, mitigants, monitoring trigger} | Every research |
| `open_questions` | What we don't know yet; what to watch | Every research; planner uses this as input |
| `recent_observations` | Timeline of notable events with our interpretation | Every research |
| `past_verdicts` | Every recommendation + price + outcome | Calibration job |
| `anti_thesis` | The strongest bear case we acknowledge as legitimate | Judge agent |

Each section carries:
```json
{ "content_md": "...",
  "structured": {...},
  "last_updated": "2026-05-17T...",
  "evidence_refs": ["evidence_id_1", "evidence_id_2"],
  "confidence": "high|medium|low" }
```

### 13.2 The distillation cycle

1. **Read**: Planner loads memo as starting context. Open Questions seeds the investigation plan.
2. **Research**: Agent loop runs, evidence accumulated.
3. **Diff proposal**: `MemoSynthesizer` LLM call: input = (old memo + new evidence + verdict). Output = proposed updated memo + a `delta_summary` listing what changed and *why*.
4. **Surface**: UI shows the diff (red strikethroughs, green additions, "newly confirmed", "newly falsified" annotations).
5. **Accept / edit / reject**: User reviews. Accepted memo becomes new version. History preserved in `living_memo_versions`.

The memo is **the single source of truth for what we know about this ticker**. Subsequent researches don't redo everything from scratch — they look at the memo's Open Questions and Risk Register and decide what's worth investigating now.

### 13.3 Memo viewer UI (`MemoPage.jsx`)

Sections collapsible. Each section shows last-updated, confidence, evidence chips. Version dropdown to compare any two versions. Manual edit toggle.

## 14. Multi-agent debate

Files: `analysis/agents/bull.py`, `bear.py`, `judge.py`, `self_critique.py`.

Each agent is a separate LLM call with separate system prompt and separate evidence view.

### 14.1 Bull agent
- System: "Long-only fundamental analyst. Build the strongest bullish case using *only* evidence in the ledger."
- Input: full `EvidenceLedger`
- Output: `{thesis_md, key_drivers: [{claim, evidence_refs, confidence}], price_target_methodology}`
- Constraint: every claim must cite ≥1 evidence ref. Uncited claims get rejected by validator.

### 14.2 Bear agent
- System: "Short-seller. (a) Attack the Bull Case for logical / evidentiary weakness. (b) Build an independent Bear Case from the same evidence."
- Input: ledger + bull thesis
- Output: `{attack_md, independent_bear_md, key_risks: [...], price_target_downside}`

### 14.3 Judge agent
- System: "Portfolio manager allocating real capital. Weigh both sides. Identify *what would change my mind* (falsifiable conditions)."
- Input: ledger + bull + bear
- Output: structured verdict:
  ```json
  { "summary", "recommendation", "conviction",
    "bull_case", "bear_case",
    "what_would_change_mind": ["if revenue growth drops below X%", ...],
    "key_catalysts", "target_price_range",
    "trade_plan": { "entry_zone", "stop_methodology", "targets", "time_stop" } }
  ```

### 14.4 Self-critique
- System: "Find the 3 weakest claims in this verdict. What evidence would falsify each? Is that evidence available but missed?"
- May trigger another planner round if it surfaces gaps.

The full debate transcript surfaces in the UI under a "Debate" tab so the user can read the reasoning.

## 15. Sector specialization

`analysis/sector_router.py` classifies each ticker into a sector profile, which determines:
- Required KPIs (which tools to call, which fields to extract)
- Peer cohort (who to compare against)
- Prompt template variants for Bull/Bear/Judge

```python
SECTOR_ANALYZERS = {
    "saas":     SaaSAnalyzer,      # ARR, NRR, Rule of 40, magic#, CAC payback
    "banks":    BankAnalyzer,      # NIM, efficiency, NPL, deposit beta, T1 cap
    "reits":    REITAnalyzer,      # FFO, AFFO, occupancy, WALT, cap-rate spread
    "biotech":  BiotechAnalyzer,   # pipeline, PDUFA, cash runway, trial readouts
    "energy":   EnergyAnalyzer,    # reserves, breakeven, F&D, production growth
    "semis":    SemisAnalyzer,     # wafer pricing, capex cycle, customer concentration
    "consumer": ConsumerAnalyzer,  # comp sales, inventory turn, brand strength
    "default":  GenericAnalyzer,
}
```

Classification uses GICS sub-industry, business description, and an LLM fallback for edge cases.

## 16. Personalization layer

### 16.1 Portfolio-aware research
`tools/correlation_analysis.py`: correlation matrix vs current holdings, sector concentration impact, factor overlap. Surfaces in verdict: *"Adding NVDA brings AI concentration to 31%; correlation w/ existing book = 0.78."*

### 16.2 Personal sizing
Extends v1's Half-Kelly with:
- Portfolio-level vol budget (target portfolio vol = 15-20%)
- Per-position cap (e.g., 10% max single)
- Per-sector cap (e.g., 35% max)
- Tax-lot awareness (if existing position underwater → wash sale window)

### 16.3 Calibration log
Every recommendation is logged to `recommendations` table with:
- Recommendation + conviction
- Price at recommendation
- Stop + targets
- Thesis summary

A nightly cron updates outcomes: `outcome_{1m, 3m, 6m, 1y}_return_pct` and a `thesis_falsified` boolean (did it hit stop or did the thesis-required conditions break).

The Calibration Dashboard shows:
- Hit rate by conviction (HIGH calls vs MEDIUM vs LOW)
- Hit rate by sector
- Avg return vs benchmark
- Brier score per conviction bucket
- Per-ticker history

**This is the trust loop.** Over months you see whether the tool's HIGH conviction actually deserves it. Calibration is what separates a tool from a vibes machine.

## 17. Catalyst calendar + active monitoring

`analysis/catalyst_calendar.py` aggregates:
- Earnings dates (yfinance)
- FDA PDUFA (RSS scraping)
- FOMC meeting dates (Fed schedule)
- CPI / NFP releases (BLS calendar)
- OPEC meetings
- Index rebalance dates
- Lockup expiries (S-1 parsing)

A daily background job (`monitoring_worker.py`) for each *owned position*:
1. Re-runs cheap tools (price action, new filings, insider, news)
2. Compares to last memo
3. If material change → flag in a daily digest
4. If `what_would_change_mind` condition triggered → urgent alert

## 18. Conversational follow-up

`POST /api/research/<ticker>/chat` accepts `{messages: [...]}`. The LLM has:
- Full report context (loaded into system prompt with caching)
- Living Memo (loaded into system prompt with caching)
- Tool registry (can call any tool mid-conversation)

So you can ask: *"Why do you think margins compress?"* and the model can call `transcripts` to cite specific management commentary, or *"What if AI capex flatlines?"* and call `dcf_valuation` with different assumptions.

## 19. New DB schema (v2)

```sql
-- Per-ticker evolving memory
CREATE TABLE living_memo (
    ticker          TEXT PRIMARY KEY,
    current_version INTEGER NOT NULL,
    content_md      TEXT NOT NULL,
    content_json    TEXT NOT NULL,     -- structured sections
    updated_at      TEXT NOT NULL
);

CREATE TABLE living_memo_versions (
    id              INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL,
    version         INTEGER NOT NULL,
    content_md      TEXT NOT NULL,
    content_json    TEXT NOT NULL,
    delta_summary   TEXT,
    source_report_id TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(ticker, version)
);

-- Audit log: every tool call in a research session
CREATE TABLE tool_call_log (
    id              INTEGER PRIMARY KEY,
    report_id       TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    args_json       TEXT NOT NULL,
    result_summary  TEXT,
    sources_json    TEXT,
    confidence      TEXT,
    cost_usd        REAL,
    latency_ms      INTEGER,
    called_at       TEXT NOT NULL
);

-- Recommendation calibration
CREATE TABLE recommendations (
    id                      INTEGER PRIMARY KEY,
    report_id               TEXT NOT NULL,
    ticker                  TEXT NOT NULL,
    recommendation          TEXT NOT NULL,    -- BUY|HOLD|TRIM|AVOID
    conviction              TEXT NOT NULL,
    price_at_recommendation REAL NOT NULL,
    target_low              REAL,
    target_high             REAL,
    stop_loss               REAL,
    thesis_summary          TEXT,
    what_would_change_mind  TEXT,
    created_at              TEXT NOT NULL,
    outcome_1m_return_pct   REAL,
    outcome_3m_return_pct   REAL,
    outcome_6m_return_pct   REAL,
    outcome_1y_return_pct   REAL,
    outcome_thesis_falsified INTEGER,
    outcome_updated_at      TEXT,
    outcome_notes           TEXT
);

CREATE TABLE catalysts (
    id          INTEGER PRIMARY KEY,
    ticker      TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    event_date  TEXT NOT NULL,
    description TEXT,
    source      TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(ticker, event_type, event_date)
);

-- Tool-specific caches (one table per heavy tool to allow targeted invalidation)
CREATE TABLE transcripts_cache (
    id                       INTEGER PRIMARY KEY,
    ticker                   TEXT NOT NULL,
    quarter                  TEXT NOT NULL,        -- "2025Q1"
    transcript_text          TEXT NOT NULL,
    guidance_extracted_json  TEXT,
    kpi_mentions_json        TEXT,
    fetched_at               TEXT NOT NULL,
    UNIQUE(ticker, quarter)
);

CREATE TABLE insider_trades_cache (
    id                INTEGER PRIMARY KEY,
    ticker            TEXT NOT NULL,
    filing_date       TEXT NOT NULL,
    insider_name      TEXT,
    insider_role      TEXT,
    transaction_type  TEXT,    -- buy|sell
    shares            REAL,
    price             REAL,
    total_value       REAL,
    raw_filing_url    TEXT,
    fetched_at        TEXT NOT NULL
);

CREATE TABLE institutional_holdings_cache (
    id                       INTEGER PRIMARY KEY,
    ticker                   TEXT NOT NULL,
    quarter                  TEXT NOT NULL,
    holder_name              TEXT NOT NULL,
    shares                   REAL,
    value_usd                REAL,
    pct_of_holder_portfolio  REAL,
    qoq_delta_shares         REAL,
    fetched_at               TEXT NOT NULL
);

CREATE TABLE options_metrics_cache (
    id              INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL,
    snapshot_date   TEXT NOT NULL,
    iv_rank         REAL,
    iv_percentile   REAL,
    put_call_ratio  REAL,
    skew            REAL,
    unusual_json    TEXT,
    fetched_at      TEXT NOT NULL,
    UNIQUE(ticker, snapshot_date)
);
```

v1 tables remain untouched.

## 20. New API endpoints (v2)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/research/<ticker>/v2/stream` | GET | Agentic SSE stream |
| `/api/research/<ticker>/v2/refresh` | POST | Force fresh agent run |
| `/api/research/<ticker>/memo` | GET | Current Living Memo |
| `/api/research/<ticker>/memo` | PUT | Manual edit |
| `/api/research/<ticker>/memo/history` | GET | Version list |
| `/api/research/<ticker>/memo/diff?from=N&to=M` | GET | Section-level diff |
| `/api/research/<ticker>/memo/accept` | POST | Accept proposed delta |
| `/api/research/<ticker>/chat` | POST | Conversational follow-up |
| `/api/research/<ticker>/tool-log` | GET | Full audit trail of a report |
| `/api/research/<ticker>/calibration` | GET | Past calls + outcomes for this ticker |
| `/api/calibration/dashboard` | GET | Global hit rate, by conviction/sector |
| `/api/catalysts` | GET | Upcoming events (filter by owned/watchlist) |
| `/api/research/<ticker>/monitor` | POST | Toggle daily-digest monitoring |
| `/api/research/<ticker>/debate` | GET | Bull/Bear/Judge transcripts for last report |

SSE event types added in v2:
- `agent_plan` — planner emitted a new plan
- `tool_call_start` / `tool_call_complete` / `tool_call_error`
- `evidence_added`
- `debate_start` / `debate_turn` (one per agent) / `debate_complete`
- `self_critique`
- `memo_delta_proposed`
- `verdict_complete`

## 21. Cost model

Per full v2 deep research with prompt caching on Claude Sonnet 4.6 ($3/MTok in, $15/MTok out, cache reads $0.30/MTok):

| Component | Calls | Est. tokens | Cost |
|---|---|---|---|
| Planner iterations | 5-10 | ~3k each | $0.05 |
| Tool-internal LLM (transcripts, filings extraction) | 5-10 | ~8k each | $0.25 |
| Bull / Bear / Judge debate | 3 | ~15k each | $0.20 |
| Self-critique | 1 | ~10k | $0.04 |
| Memo synthesis | 1 | ~20k | $0.06 |
| **Total** | | | **~$0.60** |

On Opus 4.7 (~5× cost): ~$3.00 per research. For ~50 researches/year, $30-150 total.

`budget` config in settings:
```
budget_quick:  $0.10  (fundamentals + sentiment + cached memo read)
budget_normal: $0.60  (full v2 default)
budget_deep:   $2.00  (full + transcript deep-dives + extra debate rounds)
```

## 22. Implementation phasing

| Phase | Duration | Deliverable |
|---|---|---|
| 0 | 1 wk | `tools/` package, `ToolResult`/`Source`/`EvidenceLedger`, v2 DB migrations, refactor v1 stages into Tool interface (keep v1 endpoint working) |
| 1 | 2 wks | Data-depth tools: transcripts, insider_form4, institutional_13f, options_flow, qoe_forensics, macro_context, alt_data |
| 2 | 1 wk | `agent_loop.py` + planner; formal `bull.py`/`bear.py`/`judge.py`/`self_critique.py`; v2 SSE endpoint |
| 3 | 1.5 wks | Living Memo: schema, synthesizer, diff, viewer UI, edit/accept flow |
| 4 | 1 wk | Sector router + 5-7 sector analyzers + sector peer cohorts |
| 5 | 1 wk | Portfolio-aware tools, personal sizing, calibration log + nightly outcome backfill |
| 6 | 1 wk | Catalyst calendar, monitoring daemon, daily digest, chat endpoint + UI |
| 7 | 1 wk | Polish: research log UI, source viewer modal, calibration dashboard, confidence visualization |

Each phase is independently shippable behind a UI toggle. v2 becomes default once Phase 3 is stable.

## 23. Open design questions

1. **Transcript source.** FMP API ($14/mo) is cleanest. Alternatives: scrape Seeking Alpha (ToS risk), Whisper-transcribe YouTube earnings calls (slow, audio rights). *Recommendation*: FMP for the first build.
2. **Prompt-cache strategy.** Living Memo + sector prompt template should be cached (large, stable per session). Evidence ledger varies per call → no cache.
3. **Concurrency model.** Tools are I/O-bound (HTTP); use `asyncio` in the executor. Run independent tools in parallel within each planner round.
4. **User edits vs auto-update conflict.** If user has manually edited a memo section, should auto-sync touch it? *Proposal*: respect user edits unless they accept the proposed delta.
5. **Anti-thesis seeding.** Should the bear agent be allowed to fetch *new* tools that weren't in the bull's evidence? *Proposal*: yes, with a small extra budget.
6. **Reddit weight.** Current sentiment weights Reddit 15%. WSB is famously a *contrarian* indicator at extremes. Should we add a "Reddit extreme = inverse signal" rule? *Open*.
7. **Sector classifier robustness.** GICS sub-industry covers ~80% cleanly; the rest needs LLM classification. *Proposal*: cache classification per ticker; admin override available.

## 24. Out of scope for v2

- Auto-execution of trades (still requires manual Robinhood action)
- Voice interface
- Mobile native apps
- Multi-user/permissions (single-user tool)
- Fine-tuning on personal history (revisit after ≥100 calibrated recommendations)

---

## Appendix A — Module layout (v2)

```
analysis/
├── app.py                       # Flask routes (v1 + v2)
├── agent_loop.py                # NEW: planner/executor/observer
├── living_memo.py               # NEW: read/write/diff/version
├── sector_router.py             # NEW: ticker → sector profile
├── calibration.py               # NEW: outcome tracking
├── catalyst_calendar.py         # NEW: event aggregation
├── monitoring_worker.py         # NEW: daily digest daemon
│
├── agents/
│   ├── bull.py                  # NEW
│   ├── bear.py                  # NEW
│   ├── judge.py                 # NEW
│   ├── self_critique.py         # NEW
│   ├── memo_synth.py            # NEW
│   └── planner.py               # NEW
│
├── tools/                       # NEW: tool registry
│   ├── __init__.py              # registry + Tool base class
│   ├── fundamentals.py
│   ├── financial_trends.py
│   ├── technicals.py
│   ├── dcf_valuation.py
│   ├── peer_compare.py
│   ├── sentiment.py
│   ├── edgar_filings.py
│   ├── transcripts.py           # NEW
│   ├── insider_form4.py         # NEW
│   ├── institutional_13f.py     # NEW
│   ├── options_flow.py          # NEW
│   ├── qoe_forensics.py         # NEW
│   ├── macro_context.py         # NEW
│   ├── alt_data.py              # NEW
│   ├── catalyst_lookup.py       # NEW
│   ├── competitor_compare.py    # NEW
│   ├── news_timeline.py         # NEW
│   ├── position_sizing.py
│   ├── correlation_analysis.py  # NEW
│   ├── stress_test.py           # NEW
│   ├── memo_read.py             # NEW
│   └── calibration_lookup.py    # NEW
│
├── analyzers/                   # NEW: sector specialists
│   ├── saas.py
│   ├── banks.py
│   ├── reits.py
│   ├── biotech.py
│   ├── energy.py
│   ├── semis.py
│   ├── consumer.py
│   └── generic.py
│
├── research_stream.py           # v1 — preserved
├── research_engine.py           # v1 — preserved, gradually deprecated
├── portfolio_service.py
├── db.py
├── llm_service.py
├── sentiment_service.py
├── edgar_service.py
├── rebalancing_engine.py
├── alert_worker.py
└── companies.py
```

## Appendix B — Glossary

- **Living Memo** — per-ticker versioned knowledge document maintained by the agent across research sessions.
- **Evidence Ledger** — in-memory store of all `ToolResult`s gathered during a single research session, with citations.
- **Tool** — a callable data-fetch/computation with schema, cost estimate, and citation-tagged output.
- **Verdict** — the Judge agent's structured output: recommendation, conviction, falsifiable conditions, trade plan.
- **Delta** — the proposed change to a Living Memo after a research session (subject to user accept/edit).
- **Calibration** — measured accuracy of the tool's recommendations over time, by conviction and sector.
- **Falsifiability** — explicit "what would change my mind" conditions attached to every verdict.

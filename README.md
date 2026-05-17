# Portfolio Intelligence Tool

> An AI-powered investment research platform combining real portfolio tracking, institutional-grade analysis, and a multi-agent LLM debate engine — built for individual investors who want Bloomberg Terminal capabilities without the price tag.

---

## Table of Contents

- [What Changed (v2)](#what-changed-v2)
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
  - [v2 Agentic Research Pipeline](#v2-agentic-research-pipeline)
  - [Backend Modules](#backend-modules)
  - [Tool Registry (17 tools)](#tool-registry)
  - [Agent Roster](#agent-roster)
  - [Sector Analyzers](#sector-analyzers)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the App](#running-the-app)
- [User Flows](#user-flows)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [LLM Configuration](#llm-configuration)
- [CLI Usage](#cli-usage)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## What Changed (v2)

The original tool was a fixed 8-stage research pipeline. Claude Code rewrote the research engine as a fully agentic system. Here is what is new:

| Area | Before (v1) | After (v2) |
|------|-------------|------------|
| **Research engine** | Fixed 8-stage pipeline | Agentic loop: planner decides which tools to call each round |
| **Tool system** | Inline functions in `research_engine.py` | 17 registered `Tool` subclasses with citation contracts, budget tracking, and caching |
| **LLM debate** | Single 3-pass prompt | Separate Bull / Bear / Judge / Self-Critique agents, each with structured JSON output |
| **Living Memo** | None | Per-ticker versioned knowledge document that compounds across sessions |
| **Sector specialization** | None | 7 sector analyzers (SaaS, Banks, REITs, Biotech, Energy, Semis, Consumer) with KPI templates and peer cohorts |
| **Citations** | None | Every claim cites the tool that produced it, with timestamp and confidence |
| **Budget control** | None | Per-session dollar + wall-clock budget (Quick $0.10 / Normal $0.60 / Deep $2.00) |
| **Calibration** | None | Every recommendation logged with price, targets, stop, and falsifiability conditions for outcome tracking |
| **Test suite** | None | 97 pytest tests covering tools, agents, sector router, living memo, and the full agent loop |
| **Frontend** | `DeepResearchPage` (v1 SSE) | `DeepResearchV2Page` added alongside v1 (both preserved) |

v1 endpoints, `research_engine.py`, and `research_stream.py` are fully preserved. v2 is additive.

---

## Overview

This tool connects to your real brokerage (Robinhood), runs deep multi-source AI research on any US stock or ETF, and delivers concrete, actionable portfolio decisions. The v2 research engine is built on three ideas:

1. **The tool reasons; you decide.** Every verdict includes explicit falsifiability conditions — what would change the recommendation. You decide whether the case is strong enough for your capital.
2. **Distillation over retrieval.** A Living Memo per ticker compounds understanding across sessions. Your 10th research on NVDA is genuinely deeper than your first.
3. **Every claim cites its source.** No naked numbers. Every figure traces back to the tool that produced it, the timestamp, and a confidence rating.

---

## Features

| Feature | Description |
|---------|-------------|
| **Agentic Research (v2)** | Planner LLM decides which tools to call each round. Runs until evidence is sufficient or budget is exhausted. |
| **17-Tool Registry** | Fundamentals, financial trends, technicals, DCF valuation, sentiment, EDGAR filings, QoE forensics, macro context, insider Form 4, institutional 13F, options flow, transcripts, catalyst lookup, peer compare, alt data, memo read, and more. |
| **Multi-Agent Debate** | Bull → Bear → Judge → Self-Critique. Each agent is a separate LLM call with a specialized system prompt and structured JSON output. |
| **Living Memo** | Versioned per-ticker knowledge document (10 sections). Proposed diff after every session. Full version history. |
| **Sector Specialization** | 7 sector analyzers auto-classify tickers and inject sector-specific KPI templates, peer cohorts, and prompt prefixes into the debate. |
| **Budget Profiles** | Quick (~$0.10), Normal (~$0.60), Deep (~$2.00). Hard dollar + wall-clock caps enforced per session. |
| **Calibration Tracking** | Every recommendation logged with price, targets, stop, and falsifiability conditions. Outcome tracking at 1m/3m/6m/1y. |
| **Portfolio Sync** | Robinhood OAuth + OTP, or CSV import. Live P&L, cost basis, allocation weights. |
| **Rebalancing Engine** | Conservative / Moderate / Aggressive risk profiles. TRIM / ADD / REVIEW action list. |
| **Watchlist + Alerts** | Save tickers with notes. Price-above / price-below / % change alerts. Background daemon polls every 60 seconds. |
| **S&P 500 Scanner** | Browse all 500 companies, 11 chart patterns, Spotlight categories. |
| **Streaming UI** | SSE delivers each research stage in real time as it completes. |
| **97 Tests** | Full pytest suite covering tools, agents, sector router, living memo, and end-to-end agent loop. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vite)                        │
│  Dark terminal aesthetic · Recharts · SSE streaming             │
│                                                                 │
│  Portfolio │ Deep Research v2 │ Deep Research v1 │ Watchlist    │
│  Rebalance │ Alerts │ S&P 500 Market │ LLM Settings             │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API + SSE  (port 5173 → 5001)
┌──────────────────────────▼──────────────────────────────────────┐
│                    FLASK BACKEND  (app.py)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  v2 AGENTIC ENGINE  (agent_loop.py)                     │   │
│  │                                                         │   │
│  │  Planner ──► Tool calls (parallel) ──► Re-plan          │   │
│  │                    │                                    │   │
│  │              Evidence Ledger                            │   │
│  │                    │                                    │   │
│  │         Bull ──► Bear ──► Judge ──► Self-Critique       │   │
│  │                    │                                    │   │
│  │              Memo Synthesizer                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  v1 FIXED PIPELINE  (research_stream.py) — preserved    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DATA LAYER                                             │   │
│  │  SQLite (finance.db)  ·  JSON Cache (.cache/)           │   │
│  │  17 v2 tables + 5 v1 tables                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  BACKGROUND DAEMON  (alert_worker.py)                   │   │
│  │  Price polling every 60s · Trigger recording            │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  EXTERNAL DATA SOURCES                          │
│                                                                 │
│  Robinhood (robin_stocks)    yfinance (prices + fundamentals)   │
│  Finnhub (news + ratings)    SEC EDGAR (10-K / 10-Q / Form 4)   │
│  Reddit praw (WSB sentiment) FMP (earnings transcripts)         │
│  Wikipedia (S&P 500 list)    Google Trends (pytrends, optional) │
│  Google Gemini / Anthropic Claude / Ollama (LLM)                │
└─────────────────────────────────────────────────────────────────┘
```

### v2 Agentic Research Pipeline

```
Ticker Input
    │
    ├─ 1. Bootstrap         Load Living Memo + classify sector
    ├─ 2. Planner round     LLM picks tools to call (up to 5 per round)
    ├─ 3. Tool execution    Parallel; each emits ToolResult with citations
    ├─ 4. Re-plan           Repeat rounds 2-3 until done / budget / 4 iterations
    ├─ 5. Bull agent        Strongest bull case from evidence only (cites tools)
    ├─ 6. Bear agent        Attacks bull + independent bear case (cites tools)
    ├─ 7. Judge agent       Verdict + falsifiability conditions + trade plan
    ├─ 8. Self-critique     Finds 3 weakest claims; may trigger extra research
    ├─ 9. Memo synthesis    Proposes Living Memo diff (10 sections)
    └─ 10. Persist          Report + tool log + recommendation + memo version
```

Every step streams to the frontend via SSE as it completes.

### Backend Modules

| Module | Responsibility |
|--------|---------------|
| `app.py` | Flask REST API — all routes, CORS, request handling |
| `agent_loop.py` | v2 orchestrator: planner → tools → debate → memo synth |
| `agents/planner.py` | Decides which tools to call next (LLM, JSON output) |
| `agents/bull.py` | Builds strongest bull case from evidence ledger |
| `agents/bear.py` | Attacks bull + independent bear case |
| `agents/judge.py` | Final verdict + falsifiability + trade plan |
| `agents/self_critique.py` | Finds weakest claims; may trigger more research |
| `agents/memo_synth.py` | Proposes Living Memo delta after each session |
| `tools/__init__.py` | Tool base class, ToolResult, Source, Budget, EvidenceLedger, registry |
| `living_memo.py` | Per-ticker versioned knowledge document (10 sections) |
| `sector_router.py` | Ticker → sector classification (rule-based, cached) |
| `analyzers/` | 7 sector analyzers: KPI templates, peer cohorts, prompt prefixes |
| `db.py` | SQLite abstraction — schema init, CRUD for all 22 tables |
| `llm_service.py` | Multi-provider LLM abstraction (Claude / Gemini / Ollama) |
| `research_engine.py` | v1 fixed pipeline functions — preserved, wrapped as v2 Tools |
| `research_stream.py` | v1 SSE pipeline — preserved for v1 endpoint |
| `portfolio_service.py` | Robinhood OAuth, CSV import, live P&L enrichment |
| `sentiment_service.py` | Composite sentiment scoring (news + analyst + Reddit) |
| `edgar_service.py` | SEC EDGAR 10-K/10-Q fetch + section extraction |
| `rebalancing_engine.py` | Risk-profile portfolio analysis |
| `alert_worker.py` | Background daemon polling prices for alert triggers |
| `companies.py` | S&P 500 batch fetch (legacy CLI) |

### Tool Registry

17 tools registered at startup. The planner LLM sees their names, descriptions, and JSON schemas and decides which to call each round.

| Tool | Data Source | Cache TTL | LLM? |
|------|-------------|-----------|------|
| `fundamentals` | yfinance | 4h | No |
| `financial_trends` | yfinance (8-12 quarters) | 4h | No |
| `technicals` | yfinance daily history | 1h | No |
| `dcf_valuation` | yfinance + arithmetic | 4h | No |
| `sentiment` | Finnhub + Reddit + yfinance | None (time-sensitive) | Yes |
| `edgar_filings` | SEC EDGAR 10-K/10-Q | 24h | Yes |
| `qoe_forensics` | yfinance annual statements | 24h | No |
| `macro_context` | yfinance indices (VIX, TNX, DXY, HYG) | 1h | No |
| `insider_form4` | SEC EDGAR Form 4 | 24h | No |
| `institutional_13f` | yfinance institutional holders | 7d | No |
| `options_flow` | yfinance options chain | 4h | No |
| `transcripts` | Financial Modeling Prep (FMP_API_KEY) | 24h | No |
| `catalyst_lookup` | yfinance calendar + static FOMC/CPI/NFP | 6h | No |
| `peer_compare` | yfinance sector averages | 24h | No |
| `alt_data` | Google Trends via pytrends (optional) | 24h | No |
| `memo_read` | SQLite living_memo table | Always fresh | No |
| `calibration_lookup` | SQLite recommendations table | Always fresh | No |

### Agent Roster

| Agent | Input | Output |
|-------|-------|--------|
| `planner` | Memo open questions, evidence ledger, budget, sector | `{next_calls, done, summary}` |
| `bull` | Evidence ledger | `{thesis_md, key_drivers[], price_target_methodology, catalysts[]}` |
| `bear` | Evidence ledger + bull output | `{attack_md, independent_bear_md, key_risks[], thesis_falsifiers[]}` |
| `judge` | Evidence ledger + bull + bear | `{recommendation, conviction, what_would_change_mind[], trade_plan}` |
| `self_critique` | Verdict + evidence ledger | `{weakest_claims[], should_revise_verdict, additional_tools[]}` |
| `memo_synth` | Old memo + evidence ledger + verdict | `{new_memo, delta_summary}` |

### Sector Analyzers

Auto-classifies tickers by GICS industry. Each analyzer injects sector-specific KPIs, a peer cohort, and a prompt prefix into the bull/bear/judge agents.

| Sector | Key KPIs | Required Tools |
|--------|----------|----------------|
| **SaaS** | ARR, NRR, Rule of 40, magic number, CAC payback | `transcripts`, `qoe_forensics` |
| **Banks** | NIM, efficiency ratio, NPL ratio, deposit beta, Tier 1, ROTCE | `qoe_forensics`, `macro_context` |
| **REITs** | FFO, AFFO, occupancy, WALT, cap rate spread | `macro_context` |
| **Biotech** | Pipeline phase, PDUFA dates, cash runway, trial readouts | `catalyst_lookup`, `transcripts` |
| **Energy** | Proved reserves, breakeven price, F&D costs, hedging % | `macro_context` |
| **Semis** | Wafer pricing, capex cycle, customer concentration, lead times | `options_flow`, `transcripts` |
| **Consumer** | Comp sales, inventory turn, gross margin spread, brand strength | `sentiment`, `alt_data` |
| **Generic** | Revenue growth, operating margin, ROE, FCF margin | (none required) |

---

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask 3.0** + Flask-CORS
- **SQLite** with WAL mode (22 tables, auto-migrating schema)
- **pandas** + **numpy** (data manipulation)
- **yfinance** (stock prices, fundamentals, options, holders)
- **robin_stocks** (Robinhood unofficial API)
- **praw** (Reddit API client)
- **requests** (HTTP client for EDGAR, Finnhub, FMP)

### LLM Providers (configurable)
- **Google Gemini** — `gemini-2.0-flash` (fast), `gemini-2.5-pro` (deep)
- **Anthropic Claude** — `claude-3-5-haiku` (fast), `claude-opus-4` (deep)
- **Ollama** (local) — `llama3.2`, `mistral`, any locally pulled model

### Frontend
- **React 19** + **Vite 7**
- **Recharts 3** (charts and visualizations)
- **Vanilla CSS** (dark terminal theme, glassmorphism cards)
- **EventSource API** (SSE streaming)

### External APIs (all free tier unless noted)
- **Finnhub** — news sentiment, analyst ratings (60 req/min free)
- **SEC EDGAR** — 10-K/10-Q filings, Form 4 insider trades (no key required)
- **Financial Modeling Prep** — earnings transcripts (`FMP_API_KEY`, free tier)
- **Reddit API** — WSB + r/investing sentiment (free tier)
- **Wikipedia** — S&P 500 company list (free)
- **Google Trends** — via `pytrends` (optional, no key required)

---

## Getting Started

### Prerequisites

- **Python 3.8+** — `python3 --version`
- **Node.js 18+** — `node --version`
- **pip3** — `pip3 --version`
- At least one LLM API key (Gemini, Claude) **or** a local [Ollama](https://ollama.ai) installation

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd analysis

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Install frontend dependencies
cd web && npm install && cd ..
```

### Environment Variables

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
# ── LLM Provider (choose ONE) ──────────────────────────────────

# Anthropic Claude — https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini — https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIza...

# Ollama (local, no key needed) — https://ollama.ai
OLLAMA_BASE_URL=http://localhost:11434

# ── News & Sentiment ───────────────────────────────────────────

# Finnhub — free tier, 60 req/min — https://finnhub.io
FINNHUB_API_KEY=...

# Reddit API — https://www.reddit.com/prefs/apps (type: "script")
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=PortfolioIntelligence/1.0

# ── Transcripts ────────────────────────────────────────────────

# Financial Modeling Prep — free tier — https://financialmodelingprep.com
FMP_API_KEY=...

# ── SEC EDGAR (no key needed, just your contact info) ──────────
EDGAR_USER_AGENT=YourName your@email.com
```

**Minimum required:** one LLM key (or Ollama running locally). Everything else degrades gracefully when absent.

### Running the App

**Option A — One command (recommended):**

```bash
cd analysis
bash start.sh
```

**Option B — Manual (two terminals):**

```bash
# Terminal 1 — Flask API
cd analysis
python3 app.py

# Terminal 2 — React frontend
cd analysis/web
npm run dev
```

**Access:**
- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:5001/api](http://localhost:5001/api)

---

## User Flows

### 1. Portfolio Management

**Connect Robinhood:**
1. Navigate to **Portfolio**.
2. Enter your Robinhood email, password, and OTP from your authenticator app.
3. Click **Connect** — session cached 24 hours (no password stored).
4. Click **Sync** to pull latest holdings.

**Manual CSV Import:**
```
ticker,shares,avg_cost
AAPL,10,145.50
NVDA,5,480.00
```

**What you see:** Total value, total P&L, cost basis, per-holding unrealized P&L, portfolio weight %, sector allocation.

---

### 2. Deep Research v2 (Agentic)

1. Navigate to **Deep Research v2**.
2. Enter any US ticker. Select a budget profile: **Quick**, **Normal**, or **Deep**.
3. Click **Research** — the agentic pipeline starts streaming immediately.
4. Watch live: planner rounds, tool calls (with latency and confidence), bull/bear debate, judge verdict, self-critique, memo diff.
5. The final verdict shows: **BUY / HOLD / TRIM / AVOID**, conviction, target price range, trade plan (entry zone, stop, targets, position size), and falsifiability conditions.
6. The Living Memo is updated automatically. Review the diff and accept or edit.

**Budget profiles:**

| Profile | Cost | What runs |
|---------|------|-----------|
| Quick | ~$0.10 | Fundamentals + sentiment + cached memo only |
| Normal | ~$0.60 | Full v2 default — all relevant tools + full debate |
| Deep | ~$2.00 | Extra transcript dives, additional planner rounds |

---

### 3. Deep Research v1 (Fixed Pipeline)

The original 8-stage pipeline is preserved at the **Deep Research** page. Useful when you want a fast, deterministic run without the agentic overhead.

Stages: fundamentals → financial trends → DCF valuation → technicals → risk sizing → sentiment → SEC EDGAR → AI thesis.

---

### 4. Living Memo

The Living Memo is a versioned per-ticker knowledge document with 10 sections:

| Section | What it tracks |
|---------|---------------|
| Identity | Business model, segments, geographies |
| Moat | Competitive durability, evidence, trajectory |
| Long-term thesis | Secular drivers with evidence |
| Current state | Latest fundamentals snapshot |
| Management track record | Guidance promised vs. delivered |
| Risk register | Known risks × severity × mitigant × trigger |
| Open questions | What we don't know; what to watch |
| Recent observations | Notable events with interpretation |
| Past verdicts | Every recommendation + outcome |
| Anti-thesis | Strongest bear case acknowledged |

After each research session, the Memo Synthesizer proposes a diff. You review, accept, or edit individual sections. Prior versions are retained forever.

---

### 5. Portfolio Rebalancing

1. Navigate to **Rebalance**.
2. Select risk profile: **Conservative**, **Moderate**, or **Aggressive**.

| Profile | Max Single Position | Max Sector | Min Positions |
|---------|--------------------|-----------:|:-------------:|
| Conservative | 10% | 25% | 15 |
| Moderate | 15% | 35% | 10 |
| Aggressive | 25% | 50% | 5 |

3. Receive a prioritized action list: **TRIM** (overweight), **ADD** (underweight), **REVIEW** (concentration risk).

---

### 6. Watchlist

1. Navigate to **Watchlist**.
2. Add tickers with optional notes.
3. Click the research icon on any entry to launch Deep Research v2.

---

### 7. Price Alerts

1. Navigate to **Alerts**.
2. Create an alert: ticker + condition (Price Above / Price Below / % Change Up / % Change Down) + threshold.
3. Background daemon polls every 60 seconds and marks triggered alerts in the database.

---

### 8. S&P 500 Market Scanner

1. Navigate to **Market**.
2. Browse all 500 companies sorted by Forward P/E (default) or any metric.
3. Filter by sector. Click any company for detailed metrics, price history, and financials.
4. Use the **Patterns** tab to scan 11 chart patterns with confidence scores.
5. **Spotlight** surfaces curated categories: Growth, Value, Momentum, Quality, Dividend.

---

### 9. LLM Settings

1. Navigate to **Settings**.
2. Select provider: **Gemini**, **Claude**, or **Ollama**.
3. Configure fast model (sentiment/summaries) and deep model (thesis/analysis).
4. Click **Test Connection** to verify before running research.

**Cost routing:** Fast tasks (sentiment, quick summaries) → `model_fast`. Deep tasks (thesis, EDGAR, rebalancing) → `model_deep`.

---

## API Reference

All endpoints are prefixed with `/api` and served on port `5001`.

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/portfolio/connect` | Robinhood OAuth + OTP |
| `POST` | `/api/portfolio/disconnect` | Logout and clear session |
| `POST` | `/api/portfolio/sync` | Fetch latest holdings |
| `POST` | `/api/portfolio/import` | Import holdings from CSV |
| `GET` | `/api/portfolio/holdings` | Current holdings with live P&L |
| `GET` | `/api/portfolio/summary` | Portfolio-level stats |
| `GET` | `/api/portfolio/status` | Connection status and holdings count |

### Research v2 (Agentic)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v2/research/<ticker>/stream` | SSE stream — agentic pipeline |
| `GET` | `/api/v2/research/<ticker>` | Synchronous full report (drains stream) |
| `GET` | `/api/v2/memo/<ticker>` | Current Living Memo for a ticker |
| `GET` | `/api/v2/memo/<ticker>/versions` | Memo version history |
| `GET` | `/api/v2/memo/<ticker>/version/<n>` | Specific historical memo version |
| `POST` | `/api/v2/memo/<ticker>` | Save a user-edited memo |
| `GET` | `/api/v2/recommendations/<ticker>` | Recommendation history for calibration |

Add `?budget=quick|normal|deep` to the stream endpoint. Add `?refresh=true` to bypass cache.

### Research v1 (Fixed Pipeline)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/research/<ticker>` | Full deep research report (cached 24h) |
| `GET` | `/api/research/<ticker>/stream` | SSE stream — fixed 8-stage pipeline |
| `GET` | `/api/research/reports` | All saved research reports (paginated) |
| `GET` | `/api/research/reports/<ticker>` | Research history for a ticker |
| `GET` | `/api/research/report/<report_id>` | Single report with LLM conversation logs |
| `POST` | `/api/research/compare` | Compare multiple tickers |

### Rebalancing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rebalance?profile=moderate` | Rebalancing analysis for a risk profile |

### Watchlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watchlist` | All watched tickers |
| `POST` | `/api/watchlist` | Add a ticker (`{ ticker, notes }`) |
| `DELETE` | `/api/watchlist/<ticker>` | Remove a ticker |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts` | All alerts (active and triggered) |
| `POST` | `/api/alerts` | Create alert (`{ ticker, condition, threshold }`) |
| `DELETE` | `/api/alerts/<id>` | Delete an alert |

Conditions: `above` · `below` · `change_pct_up` · `change_pct_down`

### LLM Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/settings/llm` | Current LLM configuration |
| `POST` | `/api/settings/llm` | Update provider, models, and API key |
| `POST` | `/api/settings/llm/test` | Test LLM connection |

### S&P 500 (Legacy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/companies` | All S&P 500 companies (sortable) |
| `GET` | `/api/sectors` | Sector list with aggregate stats |
| `GET` | `/api/companies/<sector>` | Companies filtered by sector |
| `GET` | `/api/company/<ticker>` | Single company detail |
| `GET` | `/api/company/<ticker>/history` | 5-year price history (cached 4h) |
| `GET` | `/api/company/<ticker>/financials` | Quarterly/annual financials (cached 24h) |
| `GET` | `/api/patterns/<pattern>/<ticker>` | Pattern analysis for a ticker |
| `GET` | `/api/stats` | Summary statistics |
| `GET` | `/api/search?q=<query>` | Search by ticker or company name |
| `POST` | `/api/refresh` | Force fresh data fetch |
| `GET` | `/api/spotlight` | Curated spotlight categories |
| `GET` | `/api/health` | Health check |

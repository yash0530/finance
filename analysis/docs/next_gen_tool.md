# Next-Gen AI Portfolio Intelligence Tool — Specification

> **Status**: Draft v0.2 — Decisions confirmed, ready to build  
> **Last Updated**: May 2026  
> **Supersedes**: `spec.md` (analysis-only tool)

---

## 1. Vision & Motivation

The existing tool is a passive S&P 500 viewer — it shows you what the market is doing, but doesn't help you *act* on it. This tool bridges that gap.

**The core idea**: Connect to your real portfolio (Robinhood or manual entry), run deep AI-powered research across fundamental analysis, technical patterns, market sentiment, and macroeconomic signals, then give you **concrete, actionable portfolio decisions** — not just data dumps.

It's part research terminal, part AI portfolio advisor, part trading journal. Think Bloomberg Terminal meets ChatGPT, built for a single investor.

---

## 2. Core Capabilities

### 2.1 Portfolio Ingestion
- **Robinhood Integration** (primary): Connect via `robin_stocks` library (unofficial API) using OAuth credentials. Pulls current holdings, average cost basis, dividends, order history.
- **Manual Entry** (fallback): CSV upload or a simple form to enter ticker + shares + avg cost.
- **Unified portfolio model**: Regardless of source, all holdings normalize into a standard internal schema.

### 2.2 Deep Research Engine
For any stock, sector, or ETF — the tool runs a multi-layer analysis:

| Layer | What It Does |
|-------|-------------|
| **Fundamental Analysis** | DCF valuation, P/E relative to sector/history, revenue/margin trends, EPS beats/misses, balance sheet health (debt/equity, current ratio) |
| **Technical Analysis** | 11 chart patterns (already built), RSI, MACD, Bollinger Bands, moving averages (50/200 DMA), support/resistance levels |
| **Market Sentiment** | News sentiment (positive/negative/neutral NLP scoring), social sentiment (Reddit/StockTwits if desired), analyst ratings aggregation |
| **Macro Context** | Sector rotation signals, interest rate sensitivity (beta to rate changes), inflation exposure |
| **AI Synthesis** | LLM reads all of the above and writes a structured investment thesis: Bull case / Bear case / Key risks / Actionable recommendation |

### 2.3 Portfolio Rebalancing Engine
- Compute current allocation (% per sector, per stock, per asset class)
- Set a **target portfolio** (risk tolerance: conservative / balanced / aggressive, or custom % targets)
- AI engine identifies: what's overweight, what's underweight, what to trim, what to add
- Output: a prioritized action list with specific trade quantities and rationale

### 2.4 Stock / Sector / ETF Research Mode
User can search or select:
- Any ticker (beyond S&P 500 — any publicly traded stock)
- A sector (pulls all relevant ETFs + top holdings)
- A specific ETF (pulls top holdings, expense ratio, performance vs. benchmark)
- S&P 500 (uses existing data pipeline)

Then runs the full Deep Research stack on the selection.

### 2.5 Alerts & Monitoring
- Price alerts (above/below threshold)
- Portfolio drawdown alerts (e.g., "notify me if portfolio drops >5% in a day")
- News alerts (significant news for held stocks)
- Earnings calendar reminders

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  React + Vite (dark terminal aesthetic, Recharts, animations)   │
│                                                                 │
│  Pages: Portfolio | Research | Rebalance | Alerts | Watchlist   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     FLASK BACKEND (app.py)                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Portfolio    │  │ Research     │  │ Rebalancing          │  │
│  │ Router       │  │ Router       │  │ Engine               │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                     │               │
│  ┌──────▼─────────────────▼─────────────────────▼───────────┐  │
│  │                  AI ANALYSIS ENGINE                       │  │
│  │  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐   │  │
│  │  │ Fundamental  │  │ Technical   │  │ Sentiment      │   │  │
│  │  │ Analyzer     │  │ Analyzer    │  │ Analyzer       │   │  │
│  │  │ (yfinance +  │  │ (existing   │  │ (News NLP +    │   │  │
│  │  │  pandas)     │  │  patterns)  │  │  LLM scoring)  │   │  │
│  │  └──────┬───────┘  └──────┬──────┘  └───────┬────────┘   │  │
│  │         └─────────────────┴──────────────────┘           │  │
│  │                          │                                │  │
│  │              ┌───────────▼──────────┐                    │  │
│  │              │   LLM Synthesizer    │                    │  │
│  │              │  (GPT-4o / Claude)   │                    │  │
│  │              │  Investment Thesis   │                    │  │
│  │              └──────────────────────┘                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               DATA LAYER                                │    │
│  │  SQLite DB  │  JSON Cache  │  File Cache (existing)     │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                        │
│                                                                 │
│  Robinhood API    yfinance        News API        LLM API       │
│  (robin_stocks)   (free, delayed) (Finnhub/etc.)  (OpenAI/      │
│                                                   Anthropic)    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 What Gets Reused From Existing Tool

| Component | Reuse |
|-----------|-------|
| `companies.py` — S&P 500 fetcher, caching, rate limiting | ✅ 100% |
| `app.py` — All 18+ existing endpoints | ✅ 100% |
| All 11 chart pattern detectors | ✅ 100% |
| All 10 spotlight category heuristics | ✅ 100% |
| All 21 React components | ✅ 100% (enhanced) |
| JSON cache infrastructure | ✅ 100% |

### 3.2 New Backend Modules

| Module | Purpose |
|--------|---------|
| `db.py` | SQLite — portfolio, watchlist, alerts, research cache |
| `portfolio_service.py` | Robinhood connector (OTP auth via `robin_stocks`) + manual entry normalization |
| `research_engine.py` | Orchestrates fundamental + technical + sentiment + SEC filing analysis |
| `llm_service.py` | Multi-provider abstraction (Claude, Gemini, Ollama). Cost-optimized routing — cheapest model for quick tasks, best for full thesis. User-configurable via Settings UI. |
| `rebalancing_engine.py` | Portfolio optimization and AI-backed trade suggestion logic |
| `sentiment_service.py` | Finnhub news + yfinance fallback + Reddit (praw) with smart composite weighting |
| `edgar_service.py` | SEC EDGAR 10-K/10-Q fetcher + LLM-powered section summarizer |
| `alert_service.py` | Background thread polling prices + news for alert triggers |

---

## 4. Data Sources & APIs

| Source | Data | Cost | Key Required |
|--------|------|------|--------------|
| `robin_stocks` | Portfolio, holdings, order history | Free | Robinhood login + OTP |
| `yfinance` | Prices, financials, fundamentals, news | Free | No |
| `Finnhub` | News, analyst ratings, earnings calendar | Free tier (60 req/min) | Yes (free signup) |
| `praw` (Reddit API) | WSB + r/investing posts/sentiment | Free tier | Yes (free signup) |
| Anthropic Claude | LLM synthesis — primary provider option | Pay-per-use | Yes |
| Google Gemini | LLM synthesis — alternative provider option | Pay-per-use | Yes |
| Ollama (local) | LLM synthesis — fully local, no cost | Free | No (local install) |
| SEC EDGAR | Full 10-K/10-Q filings | Free | No |
| Wikipedia | S&P 500 list | Free | No |

---

## 5. Key API Endpoints (New)

### Portfolio
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolio/connect/robinhood` | POST | Authenticate with Robinhood |
| `/api/portfolio/import` | POST | Manual CSV/JSON import |
| `/api/portfolio/holdings` | GET | Current holdings with live P&L |
| `/api/portfolio/summary` | GET | Total value, day gain, allocation breakdown |
| `/api/portfolio/history` | GET | Portfolio value over time |
| `/api/portfolio/rebalance` | POST | Run rebalancing analysis with target profile |

### Research
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research/<ticker>` | GET | Full deep research report for a ticker |
| `/api/research/<ticker>/fundamental` | GET | Fundamental analysis only |
| `/api/research/<ticker>/sentiment` | GET | News + sentiment analysis |
| `/api/research/<ticker>/thesis` | GET | LLM-generated investment thesis |
| `/api/research/sector/<sector>` | GET | Sector-level research |
| `/api/research/etf/<ticker>` | GET | ETF analysis (holdings, performance) |
| `/api/research/compare` | POST | Compare multiple tickers side-by-side |

### Alerts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET/POST/DELETE | Manage alerts |
| `/api/alerts/check` | GET | Run alert evaluation |

---

## 6. LLM Integration Design

### Multi-Provider LLM Routing

```
User configures in Settings:
  Provider: [Claude | Gemini | Ollama (local)]
  API Key: ••••••••••••
  Model: claude-3-5-haiku (fast) | claude-opus-4 (deep) | gemini-2.0-flash | ...

Cost-optimized routing in llm_service.py:
  - Quick sentiment score  →  cheapest/fastest model (haiku / flash)
  - Pattern explanation    →  mid-tier model
  - Full investment thesis →  best available model (configurable)
  - SEC filing summary     →  best available model (long context needed)
```

### Prompt Architecture
The LLM is given a **structured context bundle**:

```
COMPANY: {name} ({ticker})
SECTOR: {sector}

FUNDAMENTALS:
- Revenue (TTM): {revenue}, YoY Growth: {revenue_growth}
- Net Income: {net_income}, Profit Margin: {profit_margin}
- P/E (Forward): {forward_pe}, vs Sector Avg: {sector_pe_avg}
- EPS Trend: {eps_history}
- Debt/Equity: {debt_equity}

SEC FILING SUMMARY (10-K / 10-Q):
- Business description: {edgar_business_summary}
- Key risks disclosed: {edgar_risk_factors}
- MD&A highlights: {edgar_mda_summary}

TECHNICAL SIGNALS:
- Price: {price}, vs 52W High: {from_52w_high}%, vs 52W Low: {from_52w_low}%
- RSI(14): {rsi}
- 50 DMA / 200 DMA: {ma50} / {ma200}, Golden Cross: {golden_cross}
- Patterns Detected: {patterns}

SENTIMENT (smart-weighted composite score):
- Professional News (weight: 40%): {news_headlines} | Score: {news_sentiment}
- Analyst Ratings (weight: 35%): {analyst_rating}, Target: {price_target}
- Reddit WSB/Investing (weight: 15%): {reddit_sentiment} | Mentions: {reddit_mentions}
- StockTwits (weight: 10%): {stocktwits_score}
- Composite Sentiment Score: {composite_sentiment} / 10

PORTFOLIO CONTEXT (if applicable):
- Current Weight: {portfolio_weight}%
- Cost Basis: {cost_basis}, Current Return: {unrealized_pnl}%
```

### Output Schema (structured JSON from LLM)
```json
{
  "summary": "One-sentence verdict",
  "bull_case": ["reason 1", "reason 2", "reason 3"],
  "bear_case": ["risk 1", "risk 2", "risk 3"],
  "key_catalysts": ["upcoming event 1", "event 2"],
  "recommendation": "BUY | HOLD | TRIM | AVOID",
  "conviction": "HIGH | MEDIUM | LOW",
  "target_price_range": {"low": 0, "high": 0, "timeframe": "12 months"},
  "action_items": ["Specific action 1", "Specific action 2"]
}
```

---

## 7. Portfolio Rebalancing Engine

### Inputs
- Current holdings (from Robinhood or manual)
- Risk profile: Conservative / Balanced / Aggressive / Custom
- Constraints: max position size %, sector limits, cash to deploy

### Process
1. Compute current allocation matrix (by stock, sector, market cap tier)
2. Run deep research on all held positions → score each holding
3. Compare to target allocation based on risk profile
4. Generate delta: what needs to go up / down
5. LLM refines the suggested trades with narrative reasoning
6. Output: prioritized action list with specific quantities and expected impact

### Default Risk Profiles (all overridable)
| Profile | Max Single Stock | Max Sector | Equities | Cash/Bonds |
|---------|-----------------|------------|---------|------------|
| Conservative | 5% | 20% | 60% | 40% |
| Balanced | 10% | 30% | 80% | 20% |
| Aggressive | 20% | 50% | 95% | 5% |

---

## 8. UI/UX Vision

**Aesthetic**: Dark trading terminal — deep navy/black base, electric blue accents, green/red for gains/losses, JetBrains Mono for prices, glassmorphism cards with blur effects.

### Navigation Structure
```
Sidebar (persistent) + Live quote bar across the top

├── 🏠  Dashboard     — Portfolio snapshot, day P&L, top movers, triggered alerts
├── 📊  Portfolio      — Holdings table, allocation donut, rebalance CTA, history chart
├── 🔬  Research       — Search any ticker/sector/ETF → full AI report with tabs
├── ⚖️   Rebalance      — Risk profile picker, current vs. target, trade list
├── 👀  Watchlist      — Tracked stocks with mini-charts and alert badges
├── 🔔  Alerts         — Create/manage price + news + drawdown alerts
└── 📈  Market         — Existing S&P 500 analysis (patterns, spotlight, filters)
```

### Research Report Page (per ticker)
- **Overview tab**: Quick stats card + AI verdict badge (BUY/HOLD/TRIM/AVOID)
- **Fundamental tab**: Revenue/earnings charts, key ratios vs. sector peers
- **Technical tab**: Price chart with pattern overlays (existing PatternVisualization reused)
- **Sentiment tab**: News feed with NLP sentiment scores per article
- **AI Thesis tab**: Full LLM output — summary, bull/bear bullets, catalysts, action items

---

## 9. Project File Structure (Target State)

```
finance/
└── analysis/
    ├── app.py                    # Flask backend (extended, not replaced)
    ├── companies.py              # S&P 500 fetcher (unchanged)
    ├── db.py                     # NEW: SQLite schema + CRUD helpers
    ├── portfolio_service.py      # NEW: Robinhood + manual portfolio ingestion
    ├── research_engine.py        # NEW: Multi-layer analysis orchestrator
    ├── llm_service.py            # NEW: LLM prompt builder + caller
    ├── rebalancing_engine.py     # NEW: Portfolio optimization
    ├── sentiment_service.py      # NEW: News fetching + NLP sentiment
    ├── alert_service.py          # NEW: Background alert thread
    ├── requirements.txt          # Extended with robin_stocks, openai, etc.
    ├── .env                      # API keys (never committed)
    ├── .cache/                   # Existing JSON cache (unchanged)
    ├── finance.db                # NEW: SQLite database
    ├── docs/
    │   ├── spec.md               # Original spec (kept for reference)
    │   └── next_gen_tool.md      # THIS FILE — living spec
    └── web/
        └── src/
            ├── App.jsx           # Extended routing
            ├── pages/            # NEW
            │   ├── PortfolioPage.jsx
            │   ├── ResearchPage.jsx
            │   ├── RebalancePage.jsx
            │   ├── WatchlistPage.jsx
            │   └── AlertsPage.jsx
            ├── components/       # Existing + new
            │   ├── [all 21 existing components unchanged]
            │   ├── ResearchReport.jsx    # NEW: tabbed research view
            │   ├── AIThesisCard.jsx      # NEW: LLM output display
            │   ├── PortfolioTable.jsx    # NEW: holdings + P&L
            │   ├── AllocationChart.jsx   # NEW: donut + bar charts
            │   ├── WatchlistCard.jsx     # NEW: mini ticker card
            │   ├── AlertsManager.jsx     # NEW: alert CRUD UI
            │   └── NewsPanel.jsx         # NEW: news + sentiment feed
            └── utils/
                ├── api.js        # Extended with new endpoints
                └── formatters.js # NEW: price, %, date formatters
```

---

## 10. Confirmed Decisions

| # | Question | Decision |
|---|----------|----------|
| Q1 | **LLM Provider** | Multi-provider: Claude, Gemini, and local models (Ollama). User configures their key + provider in settings. Cost-optimized routing: lightweight model for quick queries, best available for full thesis generation. |
| Q2 | **News source** | Finnhub free tier (primary) + yfinance `.news` (fallback). No paid tiers. |
| Q3 | **Social sentiment** | Yes — mix of Reddit (WSB + r/investing), news sentiment, analyst ratings, with smart weighting per signal quality. |
| Q4 | **Robinhood auth** | OTP flow via `robin_stocks`. Session token cached locally. Credentials never persisted. |
| Q5 | **Alert delivery** | In-app notifications only for v1. Email alerts as future scope (Phase 2+). |
| Q6 | **Tax awareness** | Out of scope — not needed. |
| Q7 | **Asset classes** | US equities + US ETFs only. No crypto, international, or bonds. |
| Q8 | **Device target** | Desktop-first website. Mobile responsiveness is not required. |
| Q9 | **Research depth** | Maximum quality — yes, include SEC EDGAR 10-K/10-Q parsing. LLM reads actual filings for deep fundamental analysis. |
| Q10 | **Comparison mode** | Yes, in scope for v1 — compare multiple tickers side-by-side. |

---

## 11. Future Vision

- **Voice interface**: "What's my NVDA thesis today?" — Whisper STT + LLM response
- **Automated trade execution**: With broker API, execute the AI's suggestions directly
- **Backtesting engine**: Replay historical AI recommendations to validate performance
- **Multi-account support**: Merge Robinhood + 401k + taxable brokerage into one view
- **Options flow tracking**: Unusual options activity as a leading sentiment indicator
- **Earnings call transcripts**: LLM reads quarterly call transcripts for qualitative alpha
- **Custom fine-tuning**: Train on your own historical trades + outcomes
- **Collaborative mode**: Share research reports or watchlists with others

# V2 vs V3 Reconciliation Audit and Plan

Date: 2026-05-30

Baselines used:

- **V2 baseline**: `f78f048` (`style: improve card styling, web UI components, layouts, and update cache`). This is the last clear pre-Edge-terminal state before the v3 phase series starts at `725601e`.
- **V3 baseline**: `a08b21b` (`fix(ui): make recovered shell responsive`) on `edge-recovery`. This is the latest committed Edge v3 recovery state before the current working-tree fixes.
- **Working-tree note**: after this audit began, the working tree already contains partial reconciliation repairs for Stock View, Technical Patterns, and formatting. Those are treated as "already restored in current working tree", not as part of committed V3 baseline.

If the intended V2 baseline is a different commit, rerun this audit against that SHA. The conclusions will mostly hold, but endpoint and page inventories will shift.

## Page 1 - Executive Summary

V2 and V3 are not two versions of the same product surface. They are two different product philosophies wrapped around the same research brain.

**V2 is a research and portfolio analyst.** It is centered on portfolio context, calibration, monitoring, rebalance advice, research history, advisor digest, and rich S&P 500 setup discovery. Its best traits are memory, accountability, pattern-discovery richness, and investor workflow continuity. It asks: "What should I do with my money, given what I own and what we previously believed?"

**V3 is a pull-based markets terminal.** It is centered on scanning, watchlists, themes, ticker cockpit, command execution, manual refresh, no background workers, and safer cost control. Its best traits are operational clarity, deterministic tools, faster navigation, lower surprise spending, cleaner API boundaries, and a more explicit separation between free data, paid data, and LLM spend. It asks: "What should I inspect right now, and what research should I pull on demand?"

The current pain is that V3 kept many backend primitives but removed or hid several V2 surfaces that made the app feel powerful:

- Portfolio page disappeared.
- Rebalance page disappeared.
- Advisor and calibration pages disappeared.
- Outcome and monitoring workers were removed.
- Dedicated pattern dashboards disappeared.
- Company Detail disappeared and was replaced by a narrower Stock View.
- Some S&P 500 routes were renamed and split.
- Deep Research lost some visible controls and became partly subordinated to Console.
- Pattern discovery survived mostly as a screener field and technicals payload, not as a full workflow.

The correct reconciliation is **not** to revert V3. V3 fixed real problems: uncontrolled automation, broker sync complexity, too many overlapping pages, weaker route boundaries, and hidden cost triggers. The right direction is:

1. Keep V3's pull-based terminal shell.
2. Restore V2's strongest investor surfaces as pull-triggered modules.
3. Make Stock View the command center for one ticker.
4. Make Patterns, Screener, Market, and Daily Scan all feed Stock View.
5. Restore portfolio and calibration as manual, local, non-background review workflows.
6. Keep all LLM calls inside `agent_loop` or clearly budgeted command paths.
7. Preserve Living Memo as the canonical per-ticker memory, not a RAG/vector layer.

The best merged product should feel like:

> Daily Scan and Patterns find candidates. Stock View lets you inspect the candidate. Console/Research generates the thesis. Library and Living Memo preserve memory. Portfolio and Calibration help you size and learn. Everything is pull-based, cited, auditable, and honest about model limits.

## Page 2 - Exact Surface Differences

### Navigation Pages

V2 navigation from `analysis/web/src/App.jsx` and `Sidebar.jsx`:

- `Advisor`
- `Portfolio`
- `Deep Research`
- `History`
- `Rebalance`
- `Calibration`
- `S&P 500`
- `Docs`
- `LLM Settings`

V3 navigation from `analysis/web/src/App.jsx` and `Sidebar.jsx`:

- `Market`
- `Stock View`
- `Research`
- `Daily Scan`
- `Console`
- `Library`
- `Screener`
- `Settings`
- `Docs` in footer

Current working-tree reconciliation adds:

- `Patterns`

### Pages Removed In V3

These pages existed in V2 and were removed by V3:

- `AdvisorPage.jsx`
- `PortfolioPage.jsx`
- `RebalancePage.jsx`
- `CalibrationPage.jsx`
- `LLMSettingsPage.jsx` as a standalone page

V3 replacements:

- `SettingsPage.jsx` absorbs LLM settings, data tiers, and themes.
- `LibraryPage.jsx` replaces part of History and memo browsing.
- `ConsolePage.jsx` replaces some advisor/research command workflows.
- `StockViewPage.jsx` replaces Company Detail as a ticker cockpit.
- `ScreenerPage.jsx` replaces some discovery/filter workflows.
- `TerminalPage.jsx` adds the Daily Scan surface.

### Components Removed In V3

Material V2 components deleted or absent in committed V3:

- `AllocationChart.jsx`
- `CompanyDetail.jsx`
- `CompanyDetail.css`
- `HeadShouldersDashboard.jsx`
- `HeadShouldersDashboard.css`
- `PatternVisualization.jsx`
- `SpotlightDashboard.jsx`
- `SpotlightDashboard.css`
- `TechnicalPatternsDashboard.jsx`
- `TechnicalPatternsDashboard.css`

Important point: these are not just decorative removals. `TechnicalPatternsDashboard` and `PatternVisualization` were real user-facing workflows for scanning and understanding chart patterns. Their removal explains the user's "where did all my technical patterns go?" complaint.

### Components Added In V3

V3 introduced these workflow families:

- Console components: `CommandBar`, `RunHistoryRail`, `StreamView`
- Terminal components: `MoversPanel`, `NewsTape`, `WatchlistPanel`, `ThemeHeatPanel`, `HypothesesPanel`, `CatalystsPanel`, `FlowPanel`
- Stock View components: `StockHeader`, `StockChart`, `StockTechnicals`, `FundamentalsCard`, `OwnershipStrip`, `FilingsNewsTimeline`, `ThemeContext`, `StockCTABar`
- Screener components: `RulesBuilder`, `ResultsTable`
- Settings components: `ThemesEditor`, `DataTierBadges`
- Library component: `MemosTab`
- Cross-cutting: `ErrorBoundary`, `Toast`

### Backend Modules Removed In V3

These modules existed in V2 and were deleted in V3:

- `portfolio_service.py`
- `rebalancing_engine.py`
- `monitoring_worker.py`
- `outcome_worker.py`
- `companies.py`

This is the largest philosophical shift. V2 wanted to understand holdings and monitor outcomes. V3 intentionally reduced background behavior and portfolio coupling.

### Backend Modules Added In V3

V3 added:

- `console_orchestrator.py`
- `themes_service.py`
- `screener_engine.py`
- `seed_themes.py`
- `seed_screeners.py`
- `tools/movers.py`
- `tools/news_tape.py`
- `tools/price_history.py`
- `tools/sp500_lookup.py`
- `tools/sp500_refresh.py`
- `tools/theme_heat.py`
- `agents/quick_take.py`
- `agents/compare_synth.py`
- `agents/evidence_validation.py`
- `agents/bull_rebuttal.py`

Net effect: V3 improved pull-based scanning and command orchestration, but removed portfolio review and automated outcome infrastructure.

## Page 3 - Exact API Differences

### Removed V2 Endpoints

These endpoints existed in V2 and are absent in committed V3:

- `GET /api/advisor/calibration`
- `GET /api/advisor/digest`
- `POST /api/advisor/run-digest`
- `GET /api/calibration/dashboard`
- `GET /api/companies`
- `GET /api/companies/<path:sector>`
- `GET /api/company/<ticker>`
- `GET /api/company/<ticker>/financials`
- `GET /api/company/<ticker>/history`
- `GET /api/monitoring/status`
- `GET /api/patterns/<pattern_type>`
- `GET /api/patterns/<pattern_type>/<ticker>`
- `GET /api/patterns/all`
- `GET /api/patterns/head-shoulders`
- `GET /api/patterns/head-shoulders/<ticker>`
- `POST /api/portfolio/connect`
- `POST /api/portfolio/disconnect`
- `GET /api/portfolio/holdings`
- `POST /api/portfolio/import`
- `GET /api/portfolio/rebalance`
- `GET /api/portfolio/status`
- `GET /api/portfolio/summary`
- `POST /api/portfolio/sync`
- `POST /api/refresh`
- `GET /api/research/<ticker>/calibration`
- `POST /api/research/<ticker>/monitor`
- `GET /api/research/sector/<path:sector_name>`
- `GET /api/search`
- `GET /api/sectors`
- `GET /api/spotlight`
- `GET /api/spotlight/<category>`
- `GET /api/stats`

Interpretation:

- Many S&P 500 endpoints were not truly deleted; they were namespaced under `/api/market/sp500/*`.
- Pattern endpoints were truly lost from the committed V3 surface.
- Portfolio and advisor endpoints were intentionally removed from V3.
- Monitoring/calibration endpoints were removed or hidden because V3 moved away from background automation.

### Added V3 Endpoints

These endpoints are new in committed V3:

- `GET /api/chart/<ticker>`
- `POST /api/console/run`
- `GET /api/dashboard/layout`
- `POST /api/dashboard/layout`
- `GET /api/library/memos`
- `POST /api/market/refresh-sp500`
- `GET /api/market/sp500/companies`
- `GET /api/market/sp500/companies/<path:sector>`
- `GET /api/market/sp500/company/<ticker>`
- `GET /api/market/sp500/search`
- `GET /api/market/sp500/sectors`
- `GET /api/market/sp500/spotlight`
- `GET /api/market/sp500/spotlight/<category>`
- `GET /api/market/sp500/stats`
- `POST /api/research/<ticker>/memo/staged/accept`
- `POST /api/research/<ticker>/memo/staged/discard`
- `DELETE /api/research/report/<report_id>`
- `POST /api/research/reports/delete-bulk`
- `GET /api/screener/fields`
- `POST /api/screener/run`
- `GET /api/screener/saved`
- `POST /api/screener/saved`
- `DELETE /api/screener/saved/<int:screener_id>`
- `GET /api/settings/data-tier`
- `GET /api/stock/<ticker>/filings`
- `GET /api/stock/<ticker>/fundamentals`
- `GET /api/stock/<ticker>/header`
- `GET /api/stock/<ticker>/ownership`
- `GET /api/stock/<ticker>/technicals`
- `GET /api/terminal/catalysts`
- `GET /api/terminal/flow`
- `POST /api/terminal/hypothesis`
- `GET /api/terminal/movers`
- `GET /api/terminal/news`
- `GET /api/terminal/theme-heat`
- `GET /api/terminal/watchlist`
- `POST /api/terminal/watchlist`
- `DELETE /api/terminal/watchlist/<ticker>`
- `GET /api/themes`
- `POST /api/themes`
- `DELETE /api/themes/<slug>`
- `GET /api/themes/<slug>/tickers`
- `POST /api/themes/<slug>/tickers`
- `DELETE /api/themes/<slug>/tickers/<ticker>`
- `GET /api/themes/by-ticker/<ticker>`

Interpretation:

- V3 added a much better terminal API surface.
- V3 added useful single-ticker lazy sections under `/api/stock/<ticker>/*`.
- V3 added saved screeners and themes.
- V3 added explicit dashboard layout persistence.
- V3 added staged memo accept/discard, which is a major safety improvement over V2 auto-accepting memo changes.

### Unchanged Endpoints

Core research and settings endpoints that survived:

- `GET /api/catalysts`
- `GET /api/docs`
- `GET /api/docs/<slug>`
- `GET /api/health`
- `GET /api/research/<ticker>/memo`
- `PUT /api/research/<ticker>/memo`
- `GET /api/research/<ticker>/memo/history`
- `GET /api/research/<ticker>/memo/version/<int:version>`
- `GET /api/research/<ticker>/tool-log/<report_id>`
- `GET /api/research/<ticker>/v2/stream`
- `GET /api/research/report/<report_id>`
- `GET /api/research/report/<report_id>/drift`
- `GET /api/research/reports`
- `GET /api/research/reports/<ticker>`
- `GET /api/sectors/classify/<ticker>`
- `POST /api/sectors/classify/<ticker>`
- `GET /api/settings/llm`
- `POST /api/settings/llm`
- `POST /api/settings/llm/test`
- `GET /api/version`

The research brain survived. The surface area around it changed.

## Page 4 - Database and Data Model Differences

V2 had 19 schema tables:

- `_t`
- `portfolio_holdings`
- `watchlist`
- `research_cache`
- `llm_settings`
- `research_reports`
- `living_memo`
- `living_memo_versions`
- `tool_call_log`
- `recommendations`
- `catalysts`
- `transcripts_cache`
- `insider_trades_cache`
- `institutional_holdings_cache`
- `options_metrics_cache`
- `tool_result_cache`
- `sector_classification_cache`
- `monitoring_digest`
- `monitoring_enabled`

V3 has 25 schema tables:

- All V2 tables still exist in `db.py`.
- Added `living_memo_staged`
- Added `themes`
- Added `theme_tickers`
- Added `hypotheses_cache`
- Added `screener_saved`
- Added `dashboard_layout`

Important nuance:

- V3 did **not** drop the portfolio, recommendation, monitoring, or calibration tables from schema.
- V3 did remove or hide the routes/pages that use several of those tables.
- That means reconciliation can be additive and low-risk. We can restore user-facing portfolio/calibration/review surfaces without destructive migrations.

What V2 did better in data model:

- It connected reports to recommendations and outcomes more directly.
- It represented holdings as first-class context.
- It supported monitoring digest records.

What V3 did better in data model:

- It added staged memo updates, preventing Living Memo head from being silently overwritten.
- It added themes as durable user-defined research universes.
- It added hypothesis caching for low-cost quick takes.
- It added saved screeners and dashboard layout.

Reconciliation principle:

- Keep all existing tables.
- Do not alter core tables.
- Add small sibling tables only where necessary.
- Prefer "review snapshots" and "manual outcome reviews" over background workers.

## Page 5 - Research Engine and Agent Differences

### What Stayed Strong Across Both

Both V2 and V3 use the same core research architecture:

- `agent_loop.py`
- `agents/bull.py`
- `agents/bear.py`
- `agents/judge.py`
- `agents/planner.py`
- `agents/self_critique.py`
- `agents/memo_synth.py`
- `living_memo.py`
- `sector_router.py`
- `analyzers/`
- `tools/`
- `EvidenceLedger`
- budgeted `ToolResult` calls
- `/api/research/<ticker>/v2/stream`

This is the most important positive finding. V3 did not throw away the "Living Analyst" brain.

### V2 Strengths

V2's Deep Research page was more directly visible as the main product. It exposed ticker entry, budget choice, timeline, activity drawer, report view, memo delta, and research history in a way that made the system feel like a dedicated analyst.

V2 also had outcome and calibration thinking closer to the surface:

- `ticker_calibration`
- `calibration_dashboard`
- `outcome_worker`
- `monitoring_worker`
- advisor digest endpoints
- recommendation persistence

V2's weakness was that some of these capabilities leaned toward automation and background behavior, which conflicts with the current "pull-based only" rule.

### V3 Strengths

V3 added:

- `console_orchestrator.py`
- `/api/console/run`
- slash commands: `/thesis`, `/dossier`, `/why`, `/theme`, `/compare`
- `quick_take.py`
- `compare_synth.py`
- `evidence_validation.py`
- `bull_rebuttal.py`
- staged Living Memo accept/discard
- report deletion and bulk deletion
- terminal hypothesis cache

V3 also made a key product distinction:

- Quick reads are cheap, cached, and explicit.
- Deep Research remains full, cited, budgeted, and streamed.

### Reconciliation Recommendation

Keep both interaction models:

- **Console** for power-user command workflows.
- **Research page** for form-driven, high-confidence thesis workflows.
- **Stock View CTA** for context-aware ticker-specific launch.

The problem is not that Console exists. The problem is when Console becomes the only obvious path to serious research. The merged design should let the user choose:

- Button-based path from Stock View: Run Thesis, Dossier, Quick Why.
- Command path from Console: same actions, lower friction for power use.
- Library path: reopen report, inspect memo, compare drift.

## Page 6 - Market, Patterns, Screener, and Discovery Differences

### V2 Discovery

V2 had:

- S&P 500 dashboard
- Company Table
- Company Detail
- Spotlight Dashboard
- Head & Shoulders Dashboard
- Technical Patterns Dashboard
- Pattern Visualization
- Pattern routes
- S&P 500 company endpoints

V2 discovery was visually rich and broad. It gave the user a sense of "there is a lot of market structure here."

The technical pattern infra was especially valuable:

- all-pattern scan
- specific pattern scan
- per-ticker pattern scan
- confidence
- signal
- current price
- target price
- potential
- explanatory pattern panels
- chart visualization overlays via Recharts reference lines/dots

### V3 Discovery

V3 has:

- Market page
- Spotlight Panel
- Metrics Panel
- Daily Scan
- Movers
- Theme Heat
- Watchlist
- Hypotheses
- Catalysts
- News Tape
- Flow
- Screener
- saved screeners
- themes

V3 discovery is operationally better. It can answer:

- What moved?
- Which themes are hot?
- What is on my watchlist?
- What catalysts are soon?
- What does a cheap quick take say?
- Which rule-defined names match?

But V3's committed state made chart patterns too small:

- patterns appear only inside `StockTechnicals` if detected
- patterns appear as a screener field
- dedicated pattern routes/pages were removed
- chart visualization was removed

### Reconciliation Recommendation

Discovery should have four lanes:

1. **Market**: broad index/snapshot overview.
2. **Daily Scan**: today's movement and watchlist.
3. **Patterns**: technical setup discovery across universes.
4. **Screener**: user-defined deterministic rules.

All four should feed the same destination:

- click ticker -> Stock View
- from Stock View -> run research, quick take, inspect memo, compare filings/news, manage watchlist/theme membership

The current working tree already starts restoring the Patterns lane:

- `pattern_service.py`
- `/api/patterns/*`
- `TechnicalPatternsPage.jsx`
- `Patterns` nav
- Market button routes to Patterns
- Triple Top and Triple Bottom restored into research technicals

Next step should restore pattern visualization inside Stock View, not just the table.

## Page 7 - Stock View, Company Detail, and Single-Ticker Workflow

### V2 Company Detail

V2's `CompanyDetail.jsx` was rich and inspectable. It connected:

- company snapshot
- fundamentals
- history
- financials
- pattern visualizations
- company-specific exploration

It had more "full report on the company" energy.

Weakness:

- it was tied to older S&P 500/company endpoints
- it overlapped with Deep Research and Report View
- charting was Recharts-based and not as trading-native as V3

### V3 Stock View

V3's Stock View is better architected:

- `/api/stock/<ticker>/header`
- `/api/stock/<ticker>/fundamentals`
- `/api/stock/<ticker>/technicals`
- `/api/stock/<ticker>/ownership`
- `/api/stock/<ticker>/filings`
- `/api/chart/<ticker>`
- lightweight-charts candlesticks
- overlay toggles for MA20, MA50, Bollinger, VWAP
- independent section loading
- CTAs into Research and Console

Weakness:

- committed V3 was too sparse compared with Company Detail
- technical patterns were reduced to badges
- no dedicated valuation/target ladder in Stock View
- quick take and catalysts initially lived elsewhere
- watchlist/theme management was not embedded enough

Current working tree improves this:

- Stock View returns to chart-first hierarchy.
- It adds a right-side signal rail.
- It adds Quick Take, Catalysts, ticker-aware Flow, Theme Context, Watchlist.
- It fixes percent formatting and trend object rendering in fundamentals.

### Reconciliation Recommendation

Stock View should become the unified **single-ticker cockpit**:

Top band:

- ticker, company name, current price, day move, market cap, target upside
- watchlist toggle
- theme membership pills
- run thesis / dossier / quick why

Main left:

- candlestick chart
- overlay controls
- pattern overlays
- technical summary
- key fundamentals
- valuation summary

Main right:

- Quick Take
- upcoming catalysts
- flow
- latest news/filings highlights
- Living Memo health
- last report verdict

Lower sections:

- financial trends
- ownership and insider
- filings/news timeline
- patterns detail and geometry
- report history for ticker
- memo changes
- calibration/outcome history for ticker

This reconciles V2's depth with V3's cockpit structure.

## Page 8 - Portfolio, Advisor, Calibration, and Monitoring

This is the hardest reconciliation area.

### V2 Strengths

V2 understood the user as an investor with holdings:

- portfolio connect/import/sync
- holdings
- summary
- rebalance endpoint
- Advisor page
- advisor digest
- calibration dashboard
- ticker calibration
- monitoring toggle
- monitoring status
- outcome backfill

This is extremely relevant because the repo identity says:

> Single-investor research and decision-support tool. The owner is deploying $10K of personal capital.

The tool should not only find ideas. It should help decide position sizing, follow-through, and learning.

### V2 Weaknesses

V2's broker sync and background workers conflict with newer rules:

- Pull-based only.
- No background workers, cron, queues, alerts, or push notifications.
- No accidental ongoing monitoring.
- Avoid hidden data/API costs.
- Avoid false precision in calibration.

### V3 Strengths

V3 removed background automation and broker sync complexity. This improved:

- safety
- simplicity
- predictable resource usage
- testability
- local-first privacy
- compliance with user preference for pull-based workflows

### Reconciliation Recommendation

Restore portfolio and calibration, but make them pull-based and manual.

Do **not** restore Robinhood sync as default.

Recommended model:

1. **Portfolio page**
   - Manual holdings table.
   - CSV import.
   - Optional broker connector only if explicitly requested later.
   - Position exposure by sector/theme.
   - Cash assumed from user input, not guessed.

2. **Position sizing card**
   - Shows conservative size bands.
   - Uses current thesis confidence, volatility, stop distance, and user capital.
   - Explicitly labels uncertainty.

3. **Review page**
   - Pull-triggered "Review selected positions".
   - No worker.
   - Uses saved reports, current price, memo changes, catalysts.

4. **Calibration page**
   - Manual outcome marking.
   - Pull-triggered price outcome fetch.
   - Show model track record by provider/model/budget profile.
   - Exclude local/Ollama by default, as V2 already intended.

5. **Advisor digest**
   - Replace background digest with "Generate today's review" button.
   - It creates a saved review artifact.
   - It must cite reports, memos, prices, and catalysts.

This keeps the soul of V2 without violating V3's pull-only discipline.

## Page 9 - Technical Architecture Reconciliation Plan

### Guiding Principles

1. Preserve V3 shell and route boundaries.
2. Restore V2 value as modules, not as a revert.
3. Every data fetch stays a Tool or service layer.
4. No direct provider calls outside `agent_loop` or clearly budgeted agent entry points.
5. No hidden background workers.
6. No destructive DB changes.
7. Living Memo remains canonical per-ticker memory.
8. Every LLM claim remains evidence-cited.
9. Manual user review replaces automated monitoring.
10. UI should reduce duplicate workflows, not multiply pages blindly.

### Target Navigation

Recommended final nav:

- `Market`
- `Daily Scan`
- `Patterns`
- `Screener`
- `Stock View`
- `Research`
- `Console`
- `Portfolio`
- `Library`
- `Review`
- `Settings`
- `Docs`

If that feels too wide, group:

- Research: Stock View, Research, Console, Library
- Discovery: Market, Daily Scan, Patterns, Screener
- Portfolio: Portfolio, Review
- System: Settings, Docs

### Target Backend Modules

Keep:

- `agent_loop.py`
- `console_orchestrator.py`
- `living_memo.py`
- `screener_engine.py`
- `themes_service.py`
- `pattern_detectors.py`
- `pattern_service.py`

Restore or rebuild as pull-based services:

- `portfolio_service.py` as manual holdings service only
- `review_service.py` replacing `monitoring_worker.py`
- `calibration_service.py` replacing direct worker outcome backfill
- `position_sizing_service.py` if sizing logic grows beyond Judge output

Do not restore as background workers:

- `monitoring_worker.py`
- `outcome_worker.py`

### Target Endpoint Shape

Patterns:

- keep `/api/patterns/catalog`
- keep `/api/patterns/all`
- keep `/api/patterns/<pattern_type>`
- keep `/api/patterns/<pattern_type>/<ticker>`

Portfolio:

- `GET /api/portfolio/holdings`
- `POST /api/portfolio/holdings`
- `PUT /api/portfolio/holdings/<id>`
- `DELETE /api/portfolio/holdings/<id>`
- `POST /api/portfolio/import`
- `GET /api/portfolio/summary`

Review:

- `POST /api/review/portfolio`
- `POST /api/review/ticker/<ticker>`
- `GET /api/review/history`

Calibration:

- `GET /api/calibration/dashboard`
- `GET /api/research/<ticker>/calibration`
- `POST /api/calibration/refresh`
- `POST /api/recommendations/<id>/outcome`

Stock View:

- keep `/api/stock/<ticker>/*`
- add `/api/stock/<ticker>/reports`
- add `/api/stock/<ticker>/patterns`
- add `/api/stock/<ticker>/calibration`
- add `/api/stock/<ticker>/position-context` once Portfolio exists

### Data Fetching Rules

- Price/history: `price_history` Tool.
- Pattern scans: `pattern_service` calling `price_history`.
- S&P snapshot: `sp500_refresh` Tool.
- Watchlist/themes: DB services.
- Portfolio: DB service plus manual CSV import.
- Review: pulls saved reports, memos, current prices, catalysts, user-triggered only.

## Page 10 - Implementation Roadmap

### Phase 0 - Freeze and Baseline

Goal: prevent more accidental regressions.

Tasks:

- Create a `docs/v2_v3_reconciliation_plan.md` audit document. Done in this branch.
- Add a "feature inventory" test or script that lists routes and nav pages.
- Add a Playwright smoke test for each first-class nav page.
- Record current expected pages in docs and tests.
- Decide whether `Patterns` is first-class or nested under `Screener`.

Acceptance:

- Running tests makes it obvious if a first-class page disappears.

### Phase 1 - Restore Patterns Fully

Status: started in current working tree.

Tasks:

- Keep `pattern_service.py`.
- Keep `/api/patterns/*`.
- Keep `TechnicalPatternsPage.jsx`.
- Add e2e test for `#patterns`.
- Add Stock View pattern detail panel.
- Restore pattern visualization overlays from V2 `PatternVisualization.jsx`, adapted to lightweight-charts or a compact Recharts panel.
- Add tests proving all 11 detector keys are exposed by:
  - `pattern_detectors.PATTERN_DETECTORS`
  - `research_engine._detect_all_patterns`
  - `/api/patterns/catalog`
  - Screener fields

Acceptance:

- Market -> Technical Patterns opens Patterns page.
- Patterns page can scan S&P/theme/watchlist.
- Clicking a pattern row opens Stock View.
- Stock View shows detected pattern geometry or at least pattern-specific detail.

### Phase 2 - Finish Stock View as the Single-Ticker Cockpit

Tasks:

- Add last report summary.
- Add Living Memo snapshot.
- Add pattern detail section.
- Add valuation card and target ladder from existing components.
- Add report history for ticker.
- Add watchlist toggle instead of full watchlist list if cleaner.
- Add theme add/remove from ticker context.
- Ensure no card nesting and no UI overflow.

Acceptance:

- A ticker can be evaluated without leaving Stock View until the user chooses to run research.

### Phase 3 - Reconcile Research Page and Console

Tasks:

- Restore visible budget choice on Research page.
- Make Research page and Console share the same command backend.
- Let `/thesis`, `/dossier`, and Research page produce identical report objects.
- Add deep links:
  - `#research?t=NVDA&budget=normal`
  - `#console?cmd=/why%20NVDA`
- Ensure Stock View CTA uses the right path based on intent.

Acceptance:

- Console is power-user optional, not mandatory.
- Research page remains friendly and serious.

### Phase 4 - Restore Portfolio Manually

Tasks:

- Reintroduce a `Portfolio` page.
- Use existing `portfolio_holdings` table.
- Add manual holdings CRUD.
- Add CSV import.
- Add portfolio exposure by ticker, sector, and theme.
- Do not add broker sync unless explicitly requested.
- Do not add background sync.

Acceptance:

- User can model their $10K capital and holdings manually.
- No keys or broker credentials are required.

### Phase 5 - Restore Pull-Based Review and Calibration

Tasks:

- Rebuild Calibration page from V2 concepts.
- Keep recommendations table.
- Add manual outcome review.
- Add pull-triggered price outcome refresh.
- Add model/provider/budget track record views.
- Add ticker calibration inside Stock View.
- Add "Review Portfolio" button that generates an advisor-style digest on demand.

Acceptance:

- The tool can say "we were right/wrong/uncalibrated" without a background worker.
- The user sees honest model limits before sizing up.

### Phase 6 - Merge Advisor Into Review

Tasks:

- Do not restore Advisor as a separate magical page at first.
- Create `Review` as a grounded, evidence-backed artifact generator.
- Allow review scopes:
  - watchlist
  - portfolio
  - theme
  - single ticker
- Save reviews to Library.

Acceptance:

- Advisor behavior is transparent, cited, and pull-triggered.

### Phase 7 - Docs and UX Contract

Tasks:

- Update `next_gen_tool.md`.
- Update `deep_research_guide.md`.
- Update `architecture.md`.
- Add a "What changed from V2 to V3" doc.
- Add a "feature inventory" appendix.

Acceptance:

- Docs and runtime match.

## Detailed "Best Of Each" Matrix

| Area | V2 Better | V3 Better | Reconciled Decision |
|---|---|---|---|
| Product identity | Investor analyst with portfolio memory | Fast pull-based market terminal | Terminal shell plus investor memory |
| Discovery | Rich S&P/pattern dashboards | Daily Scan, themes, watchlist, screener | Four discovery lanes: Market, Daily Scan, Patterns, Screener |
| Single ticker | Company Detail richer | Stock View architecture cleaner | Make Stock View richer using Company Detail ideas |
| Research | Deep Research page central | Console orchestration powerful | Keep both paths |
| Memory | Living Memo plus calibration | Staged memo safety | Keep staged memo, restore calibration |
| Portfolio | Holdings and rebalance first-class | Removed risky broker/background complexity | Manual portfolio, pull-based review |
| Monitoring | Outcome tracking existed | Removed hidden automation | Manual review and pull refresh |
| Patterns | Full dashboard and visualizations | Better price_history Tool and stock chart | Restore dashboard and add Stock View overlays |
| Settings | LLM Settings clear | Data tier badges and themes | Unified Settings with clearer sections |
| Tests | Worker/portfolio tests | Terminal/screener/stock endpoint tests | Keep expanded V3 tests, add regression inventory |

## Open Questions For The User

These are the decisions I need from you before turning this plan into implementation tickets:

1. When you say **V2**, do you mean commit `f78f048`, or an earlier/later state?
2. Do you want `Patterns` as a top-level nav item, or nested inside `Screener`?
3. Should we restore the full V2 pattern visualization exactly, or adapt it to the V3 candlestick chart style?
4. Do you want Head & Shoulders to remain special, or should all 11 patterns be treated equally?
5. Do you want broad S&P 500 pattern scans to default to 150 tickers for speed, or scan all available tickers by default even if slower?
6. Is manual portfolio input enough, or do you eventually want broker import back?
7. If broker import returns, should Robinhood be explicitly excluded unless you request it?
8. Should `Portfolio` be top-level, or should it live under `Review`?
9. Do you want `Advisor` restored by name, or should we rename it to `Review` to make it less mystical and more auditable?
10. Should calibration include only Deep Research reports, or also Quick Takes?
11. Should local/Ollama model outputs remain excluded from calibration by default?
12. Should recommendations be tracked automatically after every thesis, or should you explicitly mark "track this"?
13. Should Living Memo updates remain staged/manual accept, or should some trusted modes auto-accept?
14. Do you want Research page budget profiles restored visibly: quick, normal, deep?
15. Should Stock View include an editable "my position / planned position" panel?
16. Should patterns influence position sizing, or only entry timing?
17. Do you want theme packs to become central to every view, including Portfolio exposure?
18. Should Daily Scan remain its own page, or should its best panels appear on Market?
19. Is the current dark terminal aesthetic good, or did V2 have a visual tone you prefer?
20. Which lost V2 page do you miss most: Portfolio, Advisor, Rebalance, Calibration, Company Detail, or Patterns?

## My Recommended Direction

My recommendation is:

1. Keep V3 as the shell.
2. Finish restoring Patterns first.
3. Make Stock View the richer Company Detail successor.
4. Restore Portfolio manually, not via broker sync.
5. Restore Calibration and Review as pull-based workflows.
6. Keep Console, but do not force the user through it.
7. Keep all new data fetches as Tools or services that call Tools.
8. Add regression tests that prevent first-class pages and endpoints from silently disappearing again.

This gives you the best of both worlds:

- V2's depth, accountability, and investor continuity.
- V3's safety, speed, pull-based discipline, and cleaner architecture.


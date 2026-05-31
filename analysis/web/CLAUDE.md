# web/ — Frontend Conventions

React 18 + Vite. Single-page app. Dark terminal aesthetic.

## Current pages (Edge v3)

Sidebar (`components/Sidebar.jsx`) is grouped as a research funnel:
- **Discover** (#discover, default): one `DiscoverPage` with tabs `Daily Scan` (default) · `Market` · `Screener` · `Patterns`
- **Research**: `Stock View` (#stock?t=) · `Research` (#research) · `Console` (#console)
- **Track**: `Library` (#library) · `Review` (#review)
- Footer: `Settings` (#settings) · `Docs` (#docs)

The four discovery surfaces live as tabs in `pages/DiscoverPage.jsx` (lazy-loaded per tab, so only the active tab's chunk is fetched). The old hashes `#market` / `#terminal` / `#screener` / `#patterns` are kept as deep-link aliases — `App.jsx` maps them to Discover with that tab pre-selected (see `DISCOVER_TABS`), and treats them as `discover` for nav highlighting. Tab buttons carry ids `#discover-tab-<id>`. A screener-preset or patterns handoff from the Market tab switches tabs locally rather than navigating.

The sidebar carries a global ticker entry (Enter → Stock View, `R→` → Research). Track rows render a shared `<ResearchLink>` (`components/ResearchLink.jsx`) that jumps straight to Deep Research. Page→Research handoff is the `onRunResearch` prop, prop-drilled from `App.jsx`.

Routing is hash-based via `src/hooks/useHashRoute.js` — no router dependency. `App.jsx` maps `page` → component.

## Page wiring

1. Create page component under `src/pages/<Name>Page.jsx`
2. Lazy-load in `App.jsx`: `const NamePage = lazy(() => import('./pages/NamePage'));`
3. Add to `renderPage()` switch in `App.jsx`
4. Add to `NAV_ITEMS` in `components/Sidebar.jsx`

## API calls

**All HTTP goes through `src/utils/api.js`.** Components never call `fetch()` directly. Add new endpoints as exported functions in that file. Keep request/response shapes documented in `analysis/docs/next_gen_tool.md` §20.

For SSE endpoints, mirror the event-type taxonomy from the spec. `streamDeepResearch` (GET/EventSource) and `streamConsole` (POST/fetch-reader) in `api.js` are the canonical patterns.

## Citation chips (Phase 7 — pending)

Every displayed numeric value sourced from a `ToolResult` should eventually render through a `<Cited>` component that shows the source on click. Until that component exists, hand-roll a `details/summary` that exposes the source JSON (see `ToolCallCard` in `DeepResearchV2Page.jsx`).

## Style

- Dark base only — no light mode
- `JetBrains Mono` for prices, IDs, code-ish content
- Glass cards: `className="glass-card"`
- Badges: `badge-{green|red|yellow|blue|purple|gray}` for status; size with `style={{ fontSize }}`
- CSS variables in `index.css` — use them; don't hardcode colors

## State

- Local state via `useState` is the default
- For cross-page state, poll in `App.jsx` and prop-drill
- No Redux / Zustand / MobX — keep dependency footprint minimal

## Testing

End-to-end via Playwright (`tests/e2e/`). Run: `npm run test:e2e`. See `tests/e2e/README.md` for setup.

When adding a new page, add at minimum a `nav.spec.js`-equivalent test that loads it and asserts the heading renders. Backend SSE behavior is integration-tested via pytest in `analysis/tests/test_agent_loop.py`; the frontend tests focus on rendering and basic form wiring.

## Don't

- Don't add framework-level deps without updating `package.json` and noting in `analysis/docs/next_gen_tool.md`
- Don't break the lazy-loading pattern (it's what keeps initial bundle small)
- Don't add a light theme until the user asks for it
- Don't use emojis in new files unless they match the existing aesthetic (current code uses them in section headers and as icons; OK to extend, not OK to add gratuitously)

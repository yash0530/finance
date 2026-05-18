# Implementation Plan: Material UI Overhaul

## Overview

Complete visual overhaul replacing the warm brown palette with Google-inspired Material Design. Implementation follows a token-first cascade strategy: replace CSS custom properties in `index.css`, then update component CSS files that reference hardcoded values, update chart inline styles, and add the `useRipple` hook. All changes are in `analysis/web/src/`.

## Tasks

- [x] 1. Replace color tokens in index.css :root
  - [x] 1.1 Replace background and accent color tokens in `analysis/web/src/index.css`
    - Replace the entire Dark Neutral Palette section (--bg-deepest through --bg-sidebar)
    - Replace all accent color tokens with Google palette (--accent-primary, --accent-blue, --accent-red, --accent-green, --accent-yellow, --accent-purple, --accent-cyan, --accent-orange, --accent-pink)
    - Add dim accent variants (--accent-green-dim, --accent-red-dim, --accent-blue-dim, --accent-yellow-dim)
    - Replace text tokens (--text-primary: #E8EAED, --text-secondary: #9AA0A6, --text-muted: #5F6368, --text-inverse: #121212)
    - Replace border tokens (--border-color, --border-color-hover, --border-sidebar)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 1.2 Replace elevation shadow tokens in `analysis/web/src/index.css`
    - Replace or add --elevation-0 through --elevation-5 with Material Design box-shadow values
    - Ensure monotonically increasing blur radius and vertical offset per level
    - _Requirements: 2.1, 2.2_

  - [x] 1.3 Replace typography scale tokens in `analysis/web/src/index.css`
    - Add --type-display-size/weight/leading/tracking (2rem, 700, 1.2, -0.02em)
    - Add --type-headline-size/weight/leading/tracking (1.5rem, 600, 1.2, -0.01em)
    - Add --type-title-size/weight/leading/tracking (1.125rem, 600, 1.4, 0em)
    - Add --type-body-size/weight/leading/tracking (0.875rem, 400, 1.5, 0em)
    - Add --type-label-size/weight/leading/tracking (0.75rem, 500, 1.4, 0.04em)
    - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [x] 2. Replace chart and sector color tokens in index.css
  - [x] 2.1 Replace chart series and sector color tokens in `analysis/web/src/index.css`
    - Replace --chart-series-1 through --chart-series-8 with Google palette order (Blue, Red, Green, Yellow, Purple, Cyan, Orange, Pink)
    - Replace --chart-grid with rgba(255, 255, 255, 0.06)
    - Replace all 11 --sector-* tokens with high-contrast values per design
    - _Requirements: 14.1, 14.3, 14.5_

- [x] 3. Update base styles and animations in index.css
  - [x] 3.1 Update scrollbar styles in `analysis/web/src/index.css`
    - Replace scrollbar thumb color with rgba(255, 255, 255, 0.15)
    - Replace scrollbar track with var(--bg-deepest)
    - Add hover state: rgba(255, 255, 255, 0.3)
    - Set width/height to 8px, border-radius to 4px
    - _Requirements: 13.1, 13.2, 13.5_

  - [x] 3.2 Update body and base element styles in `analysis/web/src/index.css`
    - Update body background to var(--bg-primary)
    - Update body color to var(--text-primary)
    - Ensure font-family references Inter
    - Remove any warm-brown hardcoded colors in base styles
    - _Requirements: 1.9, 3.2_

  - [x] 3.3 Update spinner and animation styles in `analysis/web/src/index.css`
    - Update spinner border to rgba(255, 255, 255, 0.1) track with var(--accent-blue) active segment
    - Ensure fadeIn and slideIn animations use no warm-brown color values
    - _Requirements: 13.3, 13.4_

  - [x] 3.4 Add ripple effect CSS to `analysis/web/src/index.css`
    - Add .ripple-effect class (position: absolute, border-radius: 50%, background: rgba(255,255,255,0.2), transform: scale(0), animation: ripple-animation 400ms ease-out forwards, pointer-events: none)
    - Add @keyframes ripple-animation (0%: scale(0) opacity 0.2 → 100%: scale(1) opacity 0)
    - _Requirements: 4.2, 4.3_

  - [x] 3.5 Add focus-visible global rule to `analysis/web/src/index.css`
    - Add `:focus-visible { outline: 2px solid var(--accent-blue); outline-offset: 2px; }`
    - _Requirements: 4.6_

- [x] 4. Update component primitives in index.css
  - [x] 4.1 Update .glass-card styles in `analysis/web/src/index.css`
    - Set background: var(--bg-tertiary), border: 1px solid var(--border-color), border-radius: var(--radius-lg), box-shadow: var(--elevation-1)
    - Add hover: background var(--bg-card), box-shadow var(--elevation-2), border-color var(--border-color-hover)
    - Remove any backdrop-filter or blur
    - Add transition: background 0.2s ease, box-shadow 0.2s ease
    - _Requirements: 5.1, 5.2, 5.4, 5.6, 2.3, 2.6_

  - [x] 4.2 Update button styles in `analysis/web/src/index.css`
    - Update .btn base: position relative, overflow hidden, min-height 36px, border-radius var(--radius-md)
    - Update .btn-primary: background var(--accent-blue), color white, box-shadow var(--elevation-2)
    - Update .btn-secondary: transparent bg, 1px border var(--accent-blue), color var(--accent-blue)
    - Update .btn-ghost: transparent bg, no border, color var(--accent-blue)
    - Add .btn-danger: background var(--accent-red), color white, box-shadow var(--elevation-2)
    - Update .btn:disabled: opacity 0.38, box-shadow var(--elevation-0), cursor not-allowed
    - Add .btn:focus-visible: outline 2px solid var(--accent-blue), outline-offset 2px
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 2.4_

  - [x] 4.3 Update input and form styles in `analysis/web/src/index.css`
    - Update .input/.select: background var(--bg-tertiary), border 1px solid rgba(255,255,255,0.12), border-radius var(--radius-md), min-height 36px, padding var(--spacing-sm) 12px
    - Update focus: border-color var(--accent-blue), box-shadow 0 0 0 3px rgba(66,133,244,0.2)
    - Update placeholder: color var(--text-muted)
    - Update disabled: opacity 0.38, cursor not-allowed
    - Add .input.error: border-color var(--accent-red), focus box-shadow rgba(219,68,55,0.2)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 4.4 Update table styles in `analysis/web/src/index.css`
    - Update .table-container: overflow hidden, border-radius var(--radius-lg), border 1px solid var(--border-color), box-shadow var(--elevation-1), background var(--bg-tertiary)
    - Update th: background var(--bg-secondary), color var(--text-muted), font-size var(--type-label-size), text-transform uppercase, letter-spacing var(--type-label-tracking), padding 12px 16px
    - Add th:hover: color var(--accent-blue)
    - Update td: padding 12px 16px, border-bottom 1px solid var(--border-color)
    - Update tr:hover td: background rgba(66,133,244,0.08)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 4.5 Update badge styles in `analysis/web/src/index.css`
    - Update .badge: border-radius var(--radius-pill), font-size 0.7rem, font-weight 600, padding 2px 10px
    - Update color variants: .badge-blue rgba(66,133,244,0.15) color #8ab4f8, .badge-green rgba(15,157,88,0.15) color #81c995, .badge-red rgba(219,68,55,0.15) color #f28b82, .badge-yellow rgba(244,180,0,0.15) color #fdd663
    - Update .pnl-positive: color var(--accent-green), font-family JetBrains Mono
    - Update .pnl-negative: color var(--accent-red), font-family JetBrains Mono
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 4.6 Update tab styles in `analysis/web/src/index.css`
    - Update .tabs: background var(--bg-secondary), border-radius var(--radius-lg), padding 4px
    - Update .tab-btn: min-height 48px, border-radius var(--radius-md), font-size var(--type-label-size), font-weight 500
    - Update .tab-btn:hover: background rgba(255,255,255,0.05), color var(--text-primary)
    - Update .tab-btn.active: background var(--bg-tertiary), color var(--accent-blue), box-shadow var(--elevation-1), border-bottom 2px solid var(--accent-blue)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [x] 4.7 Update alert styles in `analysis/web/src/index.css`
    - Update .alert: padding 12px 16px, border-radius var(--radius-md), box-shadow var(--elevation-1)
    - Update .alert-success: background rgba(15,157,88,0.1), border-left 3px solid var(--accent-green), color var(--accent-green)
    - Update .alert-error: background rgba(219,68,55,0.1), border-left 3px solid var(--accent-red), color var(--accent-red)
    - Update .alert-info: background rgba(66,133,244,0.1), border-left 3px solid var(--accent-blue), color var(--accent-blue)
    - Update .alert-warning: background rgba(244,180,0,0.1), border-left 3px solid var(--accent-yellow), color var(--accent-yellow)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 4.8 Update sidebar navigation styles in `analysis/web/src/index.css`
    - Update .sidebar: background var(--bg-sidebar), box-shadow 2px 0 8px rgba(0,0,0,0.3)
    - Update .nav-item: position relative, overflow hidden, border-radius var(--radius-md), transition background 0.2s ease
    - Update .nav-item:hover: background rgba(255,255,255,0.05)
    - Update .nav-item.active: background rgba(66,133,244,0.12), color var(--accent-blue), border-left 3px solid var(--accent-blue), border-radius var(--radius-md)
    - Update .nav-item.active:hover: maintain active styling
    - Update section labels: font-size var(--type-label-size), text-transform uppercase, color var(--text-muted)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 5. Checkpoint - Token and primitive verification
  - Ensure all tests pass, ask the user if questions arise. Verify: no warm-brown hex values remain in index.css, all elevation levels are defined, ripple CSS is present, focus-visible rule exists.

- [x] 6. Update App.css shell styles
  - [x] 6.1 Update `analysis/web/src/App.css` shell and layout styles
    - Remove backdrop-filter: blur(12px) from .app-header
    - Replace gradient backgrounds with solid var(--accent-blue) or var(--bg-tertiary)
    - Update .btn-refresh from purple gradient to solid blue
    - Replace var(--accent-cyan) references with var(--accent-blue)
    - Remove any remaining warm-brown hardcoded colors
    - Preserve all layout dimensions (sidebar width, topbar height, margins)
    - _Requirements: 2.7, 5.4, 9.1, 15.1, 15.6_

- [x] 7. Update component CSS files
  - [x] 7.1 Update `analysis/web/src/components/CompanyTable.css`
    - Replace rgba(212, 165, 116, 0.06) hover with rgba(66, 133, 244, 0.08)
    - Update .ticker-badge from cyan to blue
    - Update .btn-filter.active to use var(--accent-blue)
    - Remove any warm-brown hardcoded colors
    - _Requirements: 1.9, 8.3_

  - [x] 7.2 Update `analysis/web/src/components/Dashboard.css`
    - Remove var(--gradient-card) pseudo-element references
    - Replace hover transforms with elevation transitions (box-shadow var(--elevation-2))
    - Remove any backdrop-filter usage
    - Remove any warm-brown hardcoded colors
    - _Requirements: 2.6, 2.7, 5.2_

  - [x] 7.3 Update `analysis/web/src/components/SpotlightDashboard.css`
    - Replace rgba(212, 165, 116, 0.06) hover with rgba(66, 133, 244, 0.08)
    - Update .spotlight-dashboard-count from old --accent-primary to var(--accent-blue)
    - Update .sort-icon.active color to var(--accent-blue)
    - Remove any warm-brown hardcoded colors
    - _Requirements: 1.9, 8.3_

  - [x] 7.4 Update `analysis/web/src/components/SpotlightPanel.css`
    - Update any warm-toned hover/active states to blue-tinted equivalents
    - Replace any rgba(212, 165, 116, ...) with rgba(66, 133, 244, ...) or rgba(255, 255, 255, ...)
    - _Requirements: 1.9_

  - [x] 7.5 Update `analysis/web/src/components/MetricsPanel.css`
    - Update .ticker color from cyan to var(--accent-blue)
    - Update hover backgrounds to use rgba(66, 133, 244, 0.08) or rgba(255, 255, 255, 0.05)
    - Remove any warm-brown hardcoded colors
    - _Requirements: 1.9, 3.3_

  - [x] 7.6 Update `analysis/web/src/components/SearchBar.css`
    - Verify box-shadow focus ring uses new blue value rgba(66, 133, 244, 0.2)
    - Remove any warm-brown hardcoded colors
    - _Requirements: 7.2, 7.3_

  - [x] 7.7 Update `analysis/web/src/components/SectorChart.css`
    - Update tooltip contentStyle references to use Material surface colors
    - Remove any warm-brown hardcoded colors
    - _Requirements: 14.2_

  - [x] 7.8 Update `analysis/web/src/components/CompanyDetail.css`
    - Replace warm-toned accents with Google palette equivalents
    - Update any hardcoded rgba(212, 165, 116, ...) values
    - Remove any backdrop-filter usage
    - _Requirements: 1.9, 5.4_

  - [x] 7.9 Update `analysis/web/src/components/HeadShouldersDashboard.css`
    - Update any warm-toned references to use Google palette
    - Remove any warm-brown hardcoded colors
    - _Requirements: 1.9_

  - [x] 7.10 Update `analysis/web/src/components/TechnicalPatternsDashboard.css`
    - Update any warm-toned references to use Google palette
    - Remove any warm-brown hardcoded colors
    - _Requirements: 1.9_

- [x] 8. Checkpoint - CSS files verification
  - Ensure all tests pass, ask the user if questions arise. Run grep across all CSS files for old warm-brown hex values (#2a1f1e, #3b2b29, #4d3937, #5a4442, #6b4f4c, #241a19, #d4a574, #e8c49a) and rgba(212, 165, 116) — expect zero matches.

- [x] 9. Update chart components and create useRipple hook
  - [x] 9.1 Update `analysis/web/src/components/SectorChart.jsx` inline styles
    - Update Recharts Tooltip contentStyle: background '#1e1e2e', border '1px solid rgba(255,255,255,0.06)', borderRadius 8, boxShadow elevation-3 value
    - Update CartesianGrid stroke to 'rgba(255,255,255,0.06)'
    - Update axis tick fill to '#5F6368'
    - _Requirements: 14.2, 14.3, 14.6_

  - [x] 9.2 Update `analysis/web/src/components/FinancialTrendsChart.jsx` inline styles
    - Update ChartTooltip inline styles: background '#1e1e2e', border '1px solid rgba(255,255,255,0.06)', borderRadius 8
    - Update CartesianGrid stroke from rgba(45,126,247,0.08) to rgba(255,255,255,0.06)
    - Update axis tick styles to use #5F6368
    - _Requirements: 14.2, 14.3, 14.6_

  - [x] 9.3 Update `analysis/web/src/components/AllocationChart.jsx` inline styles
    - Update tooltip contentStyle: background '#1e1e2e', border '1px solid rgba(255,255,255,0.06)', borderRadius 8
    - Update CartesianGrid stroke to rgba(255,255,255,0.06)
    - Update axis tick styles to use #5F6368
    - _Requirements: 14.2, 14.3, 14.6_

  - [x] 9.4 Create `analysis/web/src/hooks/useRipple.js`
    - Create new file with useRipple hook implementation
    - Import useCallback from React
    - Implement createRipple function: calculate size from element bounding rect, position from click coordinates, create span with class 'ripple-effect', set width/height/left/top styles, append to element, remove on animationend
    - Export useRipple function
    - _Requirements: 4.1, 4.3, 4.7_

- [x] 10. Integrate useRipple into Sidebar
  - [x] 10.1 Update `analysis/web/src/components/Sidebar.jsx` to use ripple
    - Import useRipple from '../hooks/useRipple'
    - Call useRipple() to get createRipple function
    - Add createRipple(e) call to nav item button onClick handlers
    - Ensure nav-item elements have position: relative and overflow: hidden (already set in CSS task 4.8)
    - _Requirements: 4.1, 4.4_

- [x] 11. Responsive and build verification
  - [x] 11.1 Verify responsive layout preservation
    - Confirm sidebar width remains 220px, main content margin-left equals sidebar width
    - Confirm grid utilities (.grid-2, .grid-3, .grid-4) are unchanged with 768px breakpoint collapse
    - Confirm page-content max-width 1600px with auto margins is preserved
    - Confirm all utility classes (flex, flex-col, items-center, justify-between, gap-xs through gap-lg, text-center, text-right, text-muted, text-secondary, w-full, truncate) remain unchanged
    - Confirm topbar height (56px) and sidebar collapsed width (64px) tokens are preserved
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

  - [x] 11.2 Write property test: No warm brown tokens remain
    - **Property 1: No Warm Brown Tokens Remain**
    - Grep all CSS files in analysis/web/src/ for old hex values (#2a1f1e, #3b2b29, #4d3937, #5a4442, #6b4f4c, #241a19, #d4a574, #e8c49a) and verify zero matches
    - Verify no rgba(212, 165, 116, ...) patterns remain
    - **Validates: Requirements 1.9**

  - [x] 11.3 Write property test: No backdrop-filter usage
    - **Property 5: No Backdrop-Filter Usage**
    - Grep all CSS files in analysis/web/src/ for 'backdrop-filter' and verify zero matches (or only 'backdrop-filter: none')
    - **Validates: Requirements 2.7, 5.4**

  - [x] 11.4 Write property test: Elevation monotonicity
    - **Property 2: Elevation Monotonicity**
    - Parse elevation-0 through elevation-5 token values and verify blur radius and vertical offset are strictly increasing
    - **Validates: Requirements 2.1, 2.2**

  - [x] 11.5 Write property test: WCAG AA contrast compliance
    - **Property 4: WCAG AA Contrast Compliance**
    - Verify #E8EAED on #121212 ≥ 4.5:1, #9AA0A6 on #121212 ≥ 4.5:1, #5F6368 on #121212 ≥ 3:1 (large text)
    - Verify Google accent colors (#4285F4, #DB4437, #0F9D58, #F4B400) meet 3:1 against #1e1e2e
    - **Validates: Requirements 1.7, 1.10, 3.6, 10.3**

  - [x] 11.6 Write property test: Focus-visible ring consistency
    - **Property 8: Focus-Visible Ring Consistency**
    - Verify :focus-visible rule exists with outline 2px solid var(--accent-blue) and outline-offset 2px
    - **Validates: Requirements 4.6**

- [x] 12. Final checkpoint - Full build and visual audit
  - Ensure all tests pass, ask the user if questions arise. Run `npm run build` in `analysis/web/` to confirm no build errors. Perform final grep audit for warm-brown values across all modified files.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All file paths are relative to the project root (use `analysis/web/src/` not `src/`)
- No new npm dependencies are introduced — useRipple uses only React's built-in useCallback
- The token cascade means most component CSS files auto-update via var() references; component CSS tasks focus on hardcoded values only

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1", "3.2", "3.3", "3.4", "3.5"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8"] },
    { "id": 3, "tasks": ["6.1", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.9", "7.10"] },
    { "id": 4, "tasks": ["9.1", "9.2", "9.3", "9.4"] },
    { "id": 5, "tasks": ["10.1"] },
    { "id": 6, "tasks": ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6"] }
  ]
}
```

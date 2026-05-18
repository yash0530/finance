# Requirements Document

## Introduction

Complete visual overhaul of the Portfolio Intelligence web application, replacing the current dark brown/warm palette design system with a Google-inspired Material Design aesthetic. The new design centers on a neutral dark background (#121212 / #1a1a2e) with Google's signature accent colors — Red (#DB4437), Blue (#4285F4), Green (#0F9D58), and Yellow (#F4B400) — as the primary color accents throughout the interface. The overhaul implements Material Design principles including elevation surfaces, ripple interaction feedback, material typography scale, and structured component hierarchy. The scope covers the global design system (CSS custom properties, base styles), all shared UI primitives (buttons, inputs, cards, tables, badges, tabs, alerts), the sidebar navigation, and all 13 page layouts with their 38 components.

## Glossary

- **Design_System**: The centralized set of CSS custom properties, base styles, and utility classes defined in `index.css` that govern the visual appearance of the entire application
- **Material_Surface**: A UI container element styled with solid background colors and box-shadow elevation rather than transparency and backdrop-filter blur, following Material Design surface principles
- **Elevation_Level**: A numbered tier (0–5) in the Material Design shadow system that communicates visual hierarchy through progressively stronger box-shadows
- **Ripple_Effect**: A radial animation originating from the point of user interaction (click/tap) on interactive elements, providing tactile feedback per Material Design interaction patterns
- **Typography_Scale**: A predefined set of font sizes, weights, line-heights, and letter-spacing values following Material Design type scale conventions (Display, Headline, Title, Body, Label)
- **Color_Token**: A CSS custom property that stores a color value and is referenced throughout the design system to ensure consistent theming
- **Component_Primitive**: A reusable UI element (button, input, card, badge, tab, alert, table) defined in the global stylesheet and consumed across all pages
- **Sidebar_Navigation**: The fixed left-side navigation panel containing the application logo, section labels, and navigation items
- **Page_Layout**: The structural arrangement of content within the main content area for each application page
- **Google_Accent_Palette**: The four Google signature colors used as primary accents: Red (#DB4437), Blue (#4285F4), Green (#0F9D58), and Yellow (#F4B400)
- **Dark_Neutral_Palette**: The color family of neutral dark grays used for backgrounds and surfaces, ranging from #0d0d1a (deepest) to #2d2d3f (lightest surface), with no warm brown tones

## Requirements

### Requirement 1: Dark Neutral Background with Google Accent Colors

**User Story:** As a user, I want the application to use a clean dark neutral background with Google's signature red, blue, green, and yellow as vibrant accents, so that the interface feels modern, professional, and visually energetic without any warm brown tones.

#### Acceptance Criteria

1. THE Design_System SHALL define a primary background Color_Token with value #121212 or a neutral dark gray within 3 units of lightness (HSL L: 5%–10%) and a hue between 220° and 280° (cool range) with saturation no greater than 10%
2. THE Design_System SHALL define at least five and no more than eight background Color_Tokens graduated from darkest (#0d0d1a) to lightest surface (#2d2d3f) using neutral cool grays where each token has an HSL hue between 220° and 280° and saturation no greater than 15%, ensuring no token falls within the warm brown hue range (0°–50° or 330°–360°)
3. THE Design_System SHALL define Google Blue (#4285F4) as the primary accent Color_Token used for interactive elements, links, and focus states
4. THE Design_System SHALL define Google Red (#DB4437) as the danger/error accent Color_Token
5. THE Design_System SHALL define Google Green (#0F9D58) as the success/positive accent Color_Token
6. THE Design_System SHALL define Google Yellow (#F4B400) as the warning/attention accent Color_Token
7. THE Design_System SHALL define text Color_Tokens (primary at #E8EAED, secondary at #9AA0A6, muted at #5F6368) that meet WCAG AA contrast ratio of 4.5:1 for normal text (below 18.66px bold or 24px regular) and 3:1 for large text against all Dark_Neutral_Palette surface levels
8. THE Design_System SHALL define border Color_Tokens using semi-transparent white with opacity between 0.04 and 0.15 that register within the neutral cool hue range (220°–280°) when composited against the Dark_Neutral_Palette surfaces
9. WHEN a user views any page, THE Design_System SHALL render all backgrounds, surfaces, and containers using the Dark_Neutral_Palette Color_Tokens exclusively, with no rendered color having an HSL hue between 0° and 50° or between 330° and 360° at saturation above 10%
10. THE Design_System SHALL ensure all four Google_Accent_Palette colors provide sufficient contrast (WCAG AA 4.5:1 for normal text, 3:1 for large text and UI components) against the Dark_Neutral_Palette background surfaces

### Requirement 2: Material Design Elevation System

**User Story:** As a user, I want UI elements to communicate visual hierarchy through shadow-based elevation, so that I can intuitively understand which elements are foreground versus background.

#### Acceptance Criteria

1. THE Design_System SHALL define Elevation_Level tokens from level 0 (no shadow) through level 5 (maximum shadow depth), where each successive level uses a progressively larger blur radius and vertical offset in its box-shadow value
2. THE Design_System SHALL implement elevation using both box-shadow and surface color lightening, where each Elevation_Level above 0 uses a surface background color one step lighter in the Dark_Neutral_Palette (e.g., level 1 surfaces use the next lighter surface token compared to level 0 surfaces)
3. THE Design_System SHALL apply Elevation_Level 0 to flat background surfaces and Elevation_Level 1 to standard cards (glass-card class) and containers (stat-tile, table-container)
4. THE Design_System SHALL apply Elevation_Level 2 to raised interactive elements including primary buttons (btn-primary), the sidebar right edge, and floating action elements
5. THE Design_System SHALL apply Elevation_Level 3 to dropdown menus and popovers, and Elevation_Level 4 to modal dialogs
6. WHEN a user hovers over an interactive Material_Surface (cards, buttons, or navigation items), THE Design_System SHALL increase the Elevation_Level by one step within 150ms to 250ms using an ease transition
7. THE Design_System SHALL replace all existing backdrop-filter blur (glassmorphism) styles with solid Material_Surface backgrounds and elevation shadows, such that no element in the application has a computed backdrop-filter value other than none
8. IF a Component_Primitive is in a disabled state, THEN THE Design_System SHALL apply Elevation_Level 0 with no box-shadow to visually flatten the element

### Requirement 3: Material Typography Scale

**User Story:** As a user, I want consistent, readable typography that follows a structured scale, so that content hierarchy is clear and the interface feels polished.

#### Acceptance Criteria

1. THE Design_System SHALL define a Typography_Scale with at least five levels, each specifying font-size and font-weight: Display (page titles, 32px, weight 700), Headline (section headers, 24px, weight 600), Title (card headers, 18px, weight 600), Body (content text, 14px, weight 400), and Label (captions/metadata, 12px, weight 500)
2. THE Design_System SHALL use the Inter font family for all Typography_Scale levels
3. THE Design_System SHALL use the JetBrains Mono font family exclusively for numeric financial data, code snippets, and ticker symbols
4. THE Design_System SHALL define letter-spacing values per Typography_Scale level: Display at -0.02em, Headline at -0.01em, Title at 0em, Body at 0em, and Label at +0.04em
5. THE Design_System SHALL apply consistent line-height ratios: 1.2 for Display/Headline, 1.5 for Body, and 1.4 for Title/Label
6. THE Design_System SHALL render primary text in #E8EAED and secondary text in #9AA0A6, each maintaining a minimum WCAG AA contrast ratio of 4.5:1 against all Dark_Neutral_Palette surface levels
7. THE Design_System SHALL assign font-weight 500 or higher to any text rendered in JetBrains Mono to ensure monospaced numerals remain legible at small sizes

### Requirement 4: Material Interaction Feedback

**User Story:** As a user, I want visual feedback when I interact with buttons and clickable elements, so that the interface feels responsive and tactile.

#### Acceptance Criteria

1. WHEN a user clicks a button Component_Primitive, THE Design_System SHALL display a Ripple_Effect animation originating from the click coordinates, contained within the element boundaries via overflow clipping
2. THE Ripple_Effect SHALL use a semi-transparent white overlay color (rgba(255,255,255,0.2)) that is visible against the Dark_Neutral_Palette surfaces
3. THE Ripple_Effect animation SHALL complete within 400ms, with opacity transitioning from 0.2 to 0 over the final 200ms of the animation duration
4. WHEN a user clicks a navigation item in the Sidebar_Navigation, THE Design_System SHALL display a Ripple_Effect animation contained within the navigation item boundaries
5. THE Design_System SHALL apply hover state transitions with duration between 150ms and 250ms on background-color, box-shadow, border-color, and opacity properties for all interactive Component_Primitives
6. WHEN a user focuses any interactive Component_Primitive via keyboard (using :focus-visible), THE Design_System SHALL display a focus ring using Google Blue (#4285F4) with a 2px solid outline offset by 2px from the element edge
7. IF a user clicks an interactive element multiple times in rapid succession, THEN THE Design_System SHALL allow concurrent Ripple_Effect animations to overlap, with each ripple independently completing its 400ms lifecycle

### Requirement 5: Material Card and Surface Components

**User Story:** As a user, I want cards and containers to follow Material Design surface principles with neutral dark surfaces, so that the interface has clear visual structure without relying on transparency effects or warm tones.

#### Acceptance Criteria

1. THE Design_System SHALL style the glass-card class as a Material_Surface with a solid Dark_Neutral_Palette background color (#1e1e2e), border-radius of 12px, and Elevation_Level 1
2. WHEN a user hovers over a Material_Surface card, THE Design_System SHALL transition to Elevation_Level 2 and lighten the background to the next Dark_Neutral_Palette surface level (#252536) using a transition duration between 150ms and 250ms with ease timing
3. THE Design_System SHALL style stat-tile elements as Material_Surface components with Elevation_Level 1, border-radius of 12px, and internal padding of 16px on all sides
4. THE Design_System SHALL remove all backdrop-filter and blur-based transparency from card and container styles, replacing them with solid Dark_Neutral_Palette background colors
5. THE Design_System SHALL maintain consistent border-radius values: 12px for cards and top-level containers, 8px for inner elements such as inputs and nested panels, and 4px for small components such as badges and chips
6. THE Design_System SHALL apply a 1px solid border using rgba(255,255,255,0.06) on all Material_Surface card elements to define edges in the dark theme

### Requirement 6: Material Button Styles

**User Story:** As a user, I want buttons to look and behave according to Material Design conventions with Google accent colors, so that interactive elements are clearly identifiable and satisfying to use.

#### Acceptance Criteria

1. THE Design_System SHALL style btn-primary as a contained button with Google Blue (#4285F4) fill, Elevation_Level 2, white text, and minimum horizontal padding of 16px
2. THE Design_System SHALL style btn-secondary as an outlined button with a 1px border in Google Blue (#4285F4), transparent background, and Google Blue (#4285F4) text
3. THE Design_System SHALL style btn-ghost as a text button with no background or border, using Google Blue (#4285F4) for text
4. WHEN a user hovers over any button, THE Design_System SHALL increase Elevation_Level by one step, apply a background lightening overlay of rgba(255,255,255,0.08), and transition both changes within 150ms to 250ms
5. IF a button is disabled, THEN THE Design_System SHALL reduce opacity to 0.38, remove elevation shadow (Elevation_Level 0), and prevent hover and click interactions from producing visual changes
6. THE Design_System SHALL apply a minimum touch target size of 36px height for all button variants
7. THE Design_System SHALL style destructive action buttons using Google Red (#DB4437) as the fill color, white text, and Elevation_Level 2 matching btn-primary

### Requirement 7: Material Input and Form Styles

**User Story:** As a user, I want form inputs to follow Material Design patterns with clear states using Google Blue for focus indication, so that I can easily identify focused, filled, and error states.

#### Acceptance Criteria

1. THE Design_System SHALL style input elements with a solid Dark_Neutral_Palette surface color (#1e1e2e), 1px bottom border or outlined variant in rgba(255,255,255,0.12), 8px border-radius, minimum height of 36px, and horizontal padding of 12px
2. WHEN a user focuses an input, THE Design_System SHALL animate the border color to Google Blue (#4285F4) and display a 2px bottom border or outline, with the transition completing within 150ms to 250ms
3. WHEN a user focuses an input, THE Design_System SHALL display a box-shadow focus ring (0 0 0 3px with Google Blue at 20% opacity)
4. THE Design_System SHALL style placeholder text with the muted text Color_Token (#5F6368)
5. THE Design_System SHALL style select elements consistently with input elements, maintaining the same minimum height of 36px, horizontal padding of 12px, and border treatment
6. WHEN an input has a validation error, THE Design_System SHALL display the border in Google Red (#DB4437) and replace the focus ring color with Google Red at 20% opacity when focused
7. IF an input is disabled, THEN THE Design_System SHALL reduce the input opacity to 0.38 and prevent user interaction, matching the Material Design disabled state convention used for buttons

### Requirement 8: Material Table Styles

**User Story:** As a user, I want data tables to be clean and readable with clear row separation against the dark neutral background, so that I can scan financial data efficiently.

#### Acceptance Criteria

1. THE Design_System SHALL style table headers with the Typography_Scale Label level, uppercase text, a surface background one level darker than the card (#161625), and vertical padding of 12px with horizontal padding of 16px
2. THE Design_System SHALL style table rows with 12px vertical padding and 16px horizontal padding, and a 1px bottom border using rgba(255,255,255,0.06)
3. WHEN a user hovers over a table row, THE Design_System SHALL apply a background highlight of rgba(66,133,244,0.08) with a transition duration between 150ms and 250ms
4. THE Design_System SHALL style the table-container with Elevation_Level 1, border-radius of 12px, and overflow hidden for rounded corners
5. WHEN a user hovers over a sortable column header, THE Design_System SHALL change the header text color to Google Blue (#4285F4) with a transition duration between 150ms and 250ms
6. IF a table contains no data rows, THEN THE Design_System SHALL display a centered empty-state message using the Typography_Scale Body level and secondary text color (#9AA0A6) within the table-container

### Requirement 9: Material Navigation Sidebar

**User Story:** As a user, I want the sidebar navigation to follow Material Design navigation drawer patterns with the dark neutral theme, so that navigation is clear and visually integrated with the new design direction.

#### Acceptance Criteria

1. THE Sidebar_Navigation SHALL use a solid background surface color from the Dark_Neutral_Palette (#0d0d1a) with no gradient or transparency effects
2. THE Sidebar_Navigation SHALL apply Elevation_Level 2 via a right-side box-shadow to visually separate it from the main content
3. WHEN a navigation item is active, THE Sidebar_Navigation SHALL highlight it with a semi-transparent Google Blue background fill (rgba(66,133,244,0.12)), Google Blue (#4285F4) text color, and 8px border-radius on the highlight container
4. WHEN a navigation item is active, THE Sidebar_Navigation SHALL display a 3px left border indicator in Google Blue (#4285F4)
5. WHEN a user hovers over an inactive navigation item, THE Sidebar_Navigation SHALL apply a semi-transparent hover background (rgba(255,255,255,0.05)) with 8px border-radius and a transition duration between 150ms and 250ms
6. THE Sidebar_Navigation section labels SHALL use the Typography_Scale Label level with uppercase text and muted color (#5F6368)
7. WHEN a user hovers over an active navigation item, THE Sidebar_Navigation SHALL maintain the active highlight styling without applying the inactive hover background

### Requirement 10: Material Badge and Status Indicators

**User Story:** As a user, I want badges and status indicators to use the Google accent colors against dark neutral surfaces, so that I can quickly identify statuses and categories.

#### Acceptance Criteria

1. THE Design_System SHALL style badge elements with a pill shape (border-radius 999px), semi-transparent background tint of the badge color at 15% opacity, font-weight 600, and font-size between 0.7rem and 0.8rem with horizontal padding between 8px and 12px
2. THE Design_System SHALL map badge color variants to the Google_Accent_Palette: blue badges use Google Blue (#4285F4), green badges use Google Green (#0F9D58), red badges use Google Red (#DB4437), yellow badges use Google Yellow (#F4B400)
3. THE Design_System SHALL ensure all badge text colors maintain a minimum WCAG AA contrast ratio (4.5:1 for text at or below 14px, 3:1 for text above 14px bold) against the Dark_Neutral_Palette card surface (#1e1e2e)
4. THE Design_System SHALL style P&L positive values in Google Green (#0F9D58) using the JetBrains Mono font family, meeting WCAG AA contrast (4.5:1) against the card surface background (#1e1e2e)
5. THE Design_System SHALL style P&L negative values in Google Red (#DB4437) using the JetBrains Mono font family, meeting WCAG AA contrast (4.5:1) against the card surface background (#1e1e2e)
6. THE Design_System SHALL style the badge-sector class with a Google Blue-tinted semi-transparent background (rgba(66,133,244,0.15)) and a readable light blue text color from the Dark_Neutral_Palette that meets WCAG AA contrast against the card surface
7. IF a P&L value is exactly zero or null, THEN THE Design_System SHALL style it with the secondary text Color_Token (#9AA0A6) using the JetBrains Mono font family

### Requirement 11: Material Tab Component

**User Story:** As a user, I want tab navigation to follow Material Design tab patterns with Google Blue as the active indicator, so that switching between content sections feels natural and clear.

#### Acceptance Criteria

1. THE Design_System SHALL style the tabs container with a solid Dark_Neutral_Palette surface background from the graduated scale and 4px padding
2. WHILE a tab is active, THE Design_System SHALL highlight it with a filled surface background (#1e1e2e or next graduated surface level), Google Blue (#4285F4) text, and Elevation_Level 1
3. WHILE a tab is active, THE Design_System SHALL display a 2px bottom border indicator in Google Blue (#4285F4)
4. WHEN a user hovers over an inactive tab, THE Design_System SHALL apply a background highlight using rgba(255,255,255,0.05)
5. THE Design_System SHALL apply transitions of 150ms–250ms duration on background-color, color, box-shadow, and border-color properties for tab state changes
6. THE Design_System SHALL style tab text using the Typography_Scale Label level with font-weight 500
7. THE Design_System SHALL apply a minimum height of 48px to each tab element to meet Material Design touch target guidelines

### Requirement 12: Material Alert and Notification Styles

**User Story:** As a user, I want alerts and notifications to use Google's signature colors for severity levels, so that I can quickly assess the importance of system messages.

#### Acceptance Criteria

1. THE Design_System SHALL style alert-success with a Google Green-tinted background (rgba(15,157,88,0.1)) over the Dark_Neutral_Palette surface, a 3px left border in Google Green (#0F9D58), Google Green text (#0F9D58), border-radius of 8px, and internal padding of 12px 16px
2. THE Design_System SHALL style alert-error with a Google Red-tinted background (rgba(219,68,55,0.1)) over the Dark_Neutral_Palette surface, a 3px left border in Google Red (#DB4437), Google Red text (#DB4437), border-radius of 8px, and internal padding of 12px 16px
3. THE Design_System SHALL style alert-info with a Google Blue-tinted background (rgba(66,133,244,0.1)) over the Dark_Neutral_Palette surface, a 3px left border in Google Blue (#4285F4), Google Blue text (#4285F4), border-radius of 8px, and internal padding of 12px 16px
4. THE Design_System SHALL style alert-warning with a Google Yellow-tinted background (rgba(244,180,0,0.1)) over the Dark_Neutral_Palette surface, a 3px left border in Google Yellow (#F4B400), Google Yellow text (#F4B400), border-radius of 8px, and internal padding of 12px 16px
5. THE Design_System SHALL apply Elevation_Level 1 to all alert variants
6. THE Design_System SHALL ensure all alert text colors meet WCAG AA contrast ratio (4.5:1) against their respective tinted background rendered over the Dark_Neutral_Palette surface

### Requirement 13: Scrollbar and Micro-Interaction Styling

**User Story:** As a user, I want scrollbars and small UI details to match the dark neutral theme, so that the design feels cohesive down to the smallest elements.

#### Acceptance Criteria

1. THE Design_System SHALL style scrollbar thumbs with a width of 8px, border-radius of 4px, and background color of rgba(255,255,255,0.15) against a scrollbar track colored with the darkest background Color_Token (#0d0d1a)
2. THE Design_System SHALL style scrollbar tracks with the darkest background Color_Token (#0d0d1a)
3. THE Design_System SHALL maintain the existing spinner animation but update its border colors to use Google Blue (#4285F4) as the active segment and rgba(255,255,255,0.1) as the track
4. THE Design_System SHALL apply the fadeIn animation with a duration of 300ms ease-out and the slideIn animation with a duration of 300ms ease-out, ensuring all animated elements render using Dark_Neutral_Palette Color_Tokens with no warm brown tones from the previous palette
5. WHEN a user hovers over a scrollbar thumb, THE Design_System SHALL transition the thumb background color to rgba(255,255,255,0.3) within 150ms

### Requirement 14: Chart and Data Visualization Theming

**User Story:** As a user, I want charts and data visualizations to use the Google accent colors against the dark neutral background, so that financial data is presented clearly and vibrantly.

#### Acceptance Criteria

1. THE Design_System SHALL define chart series colors using the Google_Accent_Palette as the primary four colors: Blue (#4285F4), Red (#DB4437), Green (#0F9D58), Yellow (#F4B400), followed by at least 4 additional colors for series beyond four, where each additional color has a minimum perceptual difference of 30 CIEDE2000 units from every other series color
2. THE Design_System SHALL ensure the Recharts tooltip and legend components inherit the Material_Surface styling with a solid dark background (#1e1e2e), Elevation_Level 3 box-shadow, and border-radius of 8px
3. THE Design_System SHALL define a chart grid line color using rgba(255,255,255,0.06) for subtle visibility against the dark background
4. THE Design_System SHALL style sentiment indicators using Google Green (#0F9D58) for bullish, Google Yellow (#F4B400) for neutral, and Google Red (#DB4437) for bearish
5. THE Design_System SHALL define at least 11 sector Color_Tokens, each maintaining a minimum WCAG 3:1 contrast ratio against the Dark_Neutral_Palette card surface (#1e1e2e) and a minimum perceptual difference of 20 CIEDE2000 units from every other sector color
6. THE Design_System SHALL style chart axis labels and tick text using the muted text Color_Token (#5F6368) and the Typography_Scale Label level

### Requirement 15: Responsive Layout Preservation

**User Story:** As a user, I want the Material Design overhaul to maintain the existing responsive behavior, so that the application remains usable across different screen sizes.

#### Acceptance Criteria

1. THE Design_System SHALL preserve the existing sidebar width (220px) and main content margin-left equal to the sidebar width, maintaining the fixed sidebar plus scrollable main content layout structure
2. THE Design_System SHALL preserve the existing grid utility classes (grid-2 as 2-column, grid-3 as 3-column, grid-4 as 4-column equal-width grids with gap of var(--spacing-lg)) and their collapse to single-column layout at the 768px breakpoint
3. THE Design_System SHALL preserve the existing page-content max-width of 1600px with horizontal auto margins for centering
4. THE Design_System SHALL maintain all existing CSS utility classes (flex, flex-col, items-center, justify-between, justify-center, gap-xs through gap-lg, text-center, text-right, text-muted, text-secondary, w-full, truncate) with unchanged behavior
5. WHILE the viewport width is 768px or less, THE Design_System SHALL collapse multi-column grids to single-column layout, switch flex row layouts to column direction where applied by existing component breakpoints, and hide or collapse the Sidebar_Navigation to preserve content area usability
6. THE Design_System SHALL preserve the existing topbar height (56px) and sidebar collapsed width (64px) CSS custom properties with their current values

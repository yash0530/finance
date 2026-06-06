# web/ — Frontend Conventions (Rules for AI Assistants)

React 18 + Vite single-page dashboard with dark theme terminal styling.

## Design & UI Aesthetics
- **Theme**: Pure dark theme. Use CSS custom variables in `index.css` (do NOT hardcode color strings).
- **Typography**: Inter / Roboto / Outfit for content, JetBrains Mono for numbers/tickers/price codes.
- **Components**: Glassmorphism (`glass-card` class), responsive flexbox/grid layouts.
- **No Tailwind CSS**: Use vanilla CSS for modifications. Do not install Tailwind unless explicitly requested.

## Coding Conventions
- **Routing**: Simple hash-based router mapping inside `src/hooks/useHashRoute.js` and `src/App.jsx`.
- **Imports**: Lazy-load all page level components.
- **State**: Keep standard `useState`/`useEffect` hooks. No heavy global state containers (Redux, Zustand) unless requested.
- **API Wrapper**: All server operations must pass through `src/utils/api.js`. Do not run direct `fetch()` calls in individual components.

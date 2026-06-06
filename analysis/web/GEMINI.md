# web/ — Frontend Conventions (Gemini Developer Guide)

This directory contains the React 18 frontend code compiled using Vite.

- **Development Server**: Launches via `npm run dev` or `analysis/start.sh`.
- **SSE Streams**: Handled in `api.js` using `EventSource` wrappers or readable stream readers for console.
- **Dependencies**: Keep npm dependency footprint small. Always update `package.json` if installing new packages.
- **Browser Tests**: Playwright scripts live in `tests/e2e/`. Run them using `npm run test:e2e` to verify UI regression.

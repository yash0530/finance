// @ts-check
import { test, expect } from '@playwright/test';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

/**
 * Property 2: Elevation Monotonicity
 *
 * Parse elevation-0 through elevation-5 token values from index.css and verify
 * that blur radius and vertical offset are strictly increasing across levels.
 *
 * Validates: Requirements 2.1, 2.2
 */

const __dirname = dirname(fileURLToPath(import.meta.url));
const INDEX_CSS_PATH = resolve(__dirname, '../../src/index.css');

/**
 * Parse a CSS box-shadow value like "0 1px 3px rgba(0,0,0,0.24), 0 1px 2px rgba(0,0,0,0.36)"
 * and extract the first shadow's vertical offset (Y) and blur radius.
 *
 * Box-shadow syntax: offset-x offset-y blur-radius spread-radius color
 * Returns { verticalOffset: number, blurRadius: number } in px, or null for "none".
 */
function parseFirstShadow(shadowValue) {
  const trimmed = shadowValue.trim();
  if (trimmed === 'none') return null;

  // Split on commas that are NOT inside parentheses (to avoid splitting rgba values)
  const shadows = trimmed.split(/,(?![^(]*\))/);
  const first = shadows[0].trim();

  // Match: offset-x offset-y blur-radius [spread-radius] [color]
  // Values are in px (e.g. "0 1px 3px rgba(...)")
  const match = first.match(/^(-?\d+(?:\.\d+)?(?:px)?)\s+(-?\d+(?:\.\d+)?px)\s+(-?\d+(?:\.\d+)?px)/);
  if (!match) {
    throw new Error(`Could not parse shadow: "${first}"`);
  }

  const verticalOffset = parseFloat(match[2]);
  const blurRadius = parseFloat(match[3]);
  return { verticalOffset, blurRadius };
}

/**
 * Extract all --elevation-N token values from the CSS content.
 * Returns an array of raw string values indexed by level (0–5).
 */
function extractElevationTokens(cssContent) {
  const tokens = {};
  const regex = /--elevation-(\d+)\s*:\s*([^;]+);/g;
  let match;
  while ((match = regex.exec(cssContent)) !== null) {
    const level = parseInt(match[1], 10);
    tokens[level] = match[2].trim();
  }
  return tokens;
}

test.describe('Property 2: Elevation Monotonicity', () => {
  /**
   * Validates: Requirements 2.1, 2.2
   *
   * For any two elevation levels L1 < L2, the box-shadow blur radius and
   * vertical offset of L2 must be strictly greater than those of L1.
   */
  test('elevation tokens exist for levels 0 through 5', () => {
    const cssContent = readFileSync(INDEX_CSS_PATH, 'utf-8');
    const tokens = extractElevationTokens(cssContent);

    for (let level = 0; level <= 5; level++) {
      expect(
        tokens[level],
        `--elevation-${level} token must be defined in index.css`
      ).toBeDefined();
    }
  });

  test('elevation-0 is "none" (flat baseline)', () => {
    const cssContent = readFileSync(INDEX_CSS_PATH, 'utf-8');
    const tokens = extractElevationTokens(cssContent);

    expect(tokens[0].trim()).toBe('none');
  });

  test('blur radii are strictly increasing from elevation-1 to elevation-5', () => {
    const cssContent = readFileSync(INDEX_CSS_PATH, 'utf-8');
    const tokens = extractElevationTokens(cssContent);

    const blurRadii = [];
    for (let level = 1; level <= 5; level++) {
      const parsed = parseFirstShadow(tokens[level]);
      expect(parsed, `elevation-${level} must have a parseable shadow`).not.toBeNull();
      blurRadii.push({ level, blurRadius: parsed.blurRadius });
    }

    // Verify strict monotonicity: each blur radius > previous
    for (let i = 1; i < blurRadii.length; i++) {
      const prev = blurRadii[i - 1];
      const curr = blurRadii[i];
      expect(
        curr.blurRadius,
        `elevation-${curr.level} blur radius (${curr.blurRadius}px) must be strictly greater than elevation-${prev.level} blur radius (${prev.blurRadius}px)`
      ).toBeGreaterThan(prev.blurRadius);
    }
  });

  test('vertical offsets are strictly increasing from elevation-1 to elevation-5', () => {
    const cssContent = readFileSync(INDEX_CSS_PATH, 'utf-8');
    const tokens = extractElevationTokens(cssContent);

    const offsets = [];
    for (let level = 1; level <= 5; level++) {
      const parsed = parseFirstShadow(tokens[level]);
      expect(parsed, `elevation-${level} must have a parseable shadow`).not.toBeNull();
      offsets.push({ level, verticalOffset: parsed.verticalOffset });
    }

    // Verify strict monotonicity: each vertical offset > previous
    for (let i = 1; i < offsets.length; i++) {
      const prev = offsets[i - 1];
      const curr = offsets[i];
      expect(
        curr.verticalOffset,
        `elevation-${curr.level} vertical offset (${curr.verticalOffset}px) must be strictly greater than elevation-${prev.level} vertical offset (${prev.verticalOffset}px)`
      ).toBeGreaterThan(prev.verticalOffset);
    }
  });

  test('reports all elevation levels with their parsed values', () => {
    const cssContent = readFileSync(INDEX_CSS_PATH, 'utf-8');
    const tokens = extractElevationTokens(cssContent);

    // elevation-0 is "none" — skip parsing
    console.log('elevation-0: none (baseline)');

    const results = [];
    for (let level = 1; level <= 5; level++) {
      const parsed = parseFirstShadow(tokens[level]);
      results.push({
        level,
        raw: tokens[level],
        verticalOffset: parsed.verticalOffset,
        blurRadius: parsed.blurRadius,
      });
      console.log(
        `elevation-${level}: verticalOffset=${parsed.verticalOffset}px, blurRadius=${parsed.blurRadius}px`
      );
    }

    // Verify the expected values from the spec
    const expectedBlurRadii  = [3, 6, 20, 28, 38];  // levels 1–5
    const expectedVOffsets   = [1, 3, 10, 14, 19];  // levels 1–5

    for (let i = 0; i < results.length; i++) {
      const { level, blurRadius, verticalOffset } = results[i];
      expect(blurRadius).toBe(
        expectedBlurRadii[i],
        `elevation-${level} blur radius should be ${expectedBlurRadii[i]}px`
      );
      expect(verticalOffset).toBe(
        expectedVOffsets[i],
        `elevation-${level} vertical offset should be ${expectedVOffsets[i]}px`
      );
    }
  });
});

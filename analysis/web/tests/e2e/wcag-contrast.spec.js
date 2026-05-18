// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Property 4: WCAG AA Contrast Compliance
 *
 * Verifies that all text and accent colors defined in the Material UI
 * design token system meet WCAG AA contrast ratio requirements against
 * their expected surface backgrounds.
 *
 * Validates: Requirements 1.7, 1.10, 3.6, 10.3
 *
 * WCAG contrast ratio formula:
 *   - Relative luminance L = 0.2126*R + 0.7152*G + 0.0722*B (linearized)
 *   - sRGB linearization: c <= 0.04045 → c/12.92, else ((c+0.055)/1.055)^2.4
 *   - Contrast ratio = (L_lighter + 0.05) / (L_darker + 0.05)
 *
 * WCAG AA thresholds:
 *   - Normal text (< 18.66px bold or < 24px regular): ≥ 4.5:1
 *   - Large text (≥ 18.66px bold or ≥ 24px regular) and UI components: ≥ 3:1
 */

// ── WCAG Contrast Utilities ──────────────────────────────────────────────────

/**
 * Convert an 8-bit sRGB channel value (0–255) to linear light.
 * @param {number} c - sRGB channel value (0–255)
 * @returns {number} linearized value (0–1)
 */
function srgbToLinear(c) {
    const normalized = c / 255;
    return normalized <= 0.04045
        ? normalized / 12.92
        : Math.pow((normalized + 0.055) / 1.055, 2.4);
}

/**
 * Compute relative luminance of an RGB color per WCAG 2.1.
 * @param {number} r - Red channel (0–255)
 * @param {number} g - Green channel (0–255)
 * @param {number} b - Blue channel (0–255)
 * @returns {number} relative luminance (0–1)
 */
function luminance(r, g, b) {
    return (
        0.2126 * srgbToLinear(r) +
        0.7152 * srgbToLinear(g) +
        0.0722 * srgbToLinear(b)
    );
}

/**
 * Compute WCAG contrast ratio between two luminance values.
 * @param {number} l1 - Luminance of first color
 * @param {number} l2 - Luminance of second color
 * @returns {number} contrast ratio (always ≥ 1)
 */
function contrastRatio(l1, l2) {
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Parse a hex color string to RGB components.
 * @param {string} hex - Hex color (e.g. '#4285F4' or '4285F4')
 * @returns {{ r: number, g: number, b: number }}
 */
function hexToRgb(hex) {
    const clean = hex.replace('#', '');
    return {
        r: parseInt(clean.slice(0, 2), 16),
        g: parseInt(clean.slice(2, 4), 16),
        b: parseInt(clean.slice(4, 6), 16),
    };
}

/**
 * Compute contrast ratio between two hex colors.
 * @param {string} fgHex - Foreground color hex
 * @param {string} bgHex - Background color hex
 * @returns {number} WCAG contrast ratio
 */
function hexContrastRatio(fgHex, bgHex) {
    const fg = hexToRgb(fgHex);
    const bg = hexToRgb(bgHex);
    const lFg = luminance(fg.r, fg.g, fg.b);
    const lBg = luminance(bg.r, bg.g, bg.b);
    return contrastRatio(lFg, lBg);
}

// ── Design Token Constants ───────────────────────────────────────────────────

const COLORS = {
    // Backgrounds
    BG_PRIMARY:  '#121212',  // Page background (elevation 0)
    BG_TERTIARY: '#1e1e2e',  // Cards at rest (elevation 1)

    // Text tokens
    TEXT_PRIMARY:   '#E8EAED',  // Normal text — requires ≥ 4.5:1
    TEXT_SECONDARY: '#9AA0A6',  // Normal text — requires ≥ 4.5:1
    TEXT_MUTED:     '#5F6368',  // Large text only — requires ≥ 3:1

    // Google Accent Palette — UI components require ≥ 3:1
    ACCENT_BLUE:   '#4285F4',
    ACCENT_RED:    '#DB4437',
    ACCENT_GREEN:  '#0F9D58',
    ACCENT_YELLOW: '#F4B400',
};

// ── Property Tests ───────────────────────────────────────────────────────────

test.describe('Property 4: WCAG AA Contrast Compliance', () => {

    // ── Utility: sRGB linearization ──────────────────────────────────────────

    test('sRGB linearization: values ≤ 0.04045 use linear segment', () => {
        // c = 10 → normalized = 10/255 ≈ 0.0392 ≤ 0.04045 → linear
        const result = srgbToLinear(10);
        expect(result).toBeCloseTo(10 / 255 / 12.92, 6);
    });

    test('sRGB linearization: values > 0.04045 use gamma segment', () => {
        // c = 128 → normalized ≈ 0.502 > 0.04045 → gamma
        const result = srgbToLinear(128);
        const expected = Math.pow((128 / 255 + 0.055) / 1.055, 2.4);
        expect(result).toBeCloseTo(expected, 6);
    });

    test('sRGB linearization: black (0) → 0, white (255) → 1', () => {
        expect(srgbToLinear(0)).toBeCloseTo(0, 6);
        expect(srgbToLinear(255)).toBeCloseTo(1, 6);
    });

    // ── Utility: luminance ───────────────────────────────────────────────────

    test('luminance: pure black (#000000) = 0', () => {
        expect(luminance(0, 0, 0)).toBeCloseTo(0, 6);
    });

    test('luminance: pure white (#FFFFFF) = 1', () => {
        expect(luminance(255, 255, 255)).toBeCloseTo(1, 6);
    });

    // ── Utility: contrast ratio ──────────────────────────────────────────────

    test('contrast ratio: black on white = 21:1', () => {
        const lWhite = luminance(255, 255, 255);
        const lBlack = luminance(0, 0, 0);
        expect(contrastRatio(lWhite, lBlack)).toBeCloseTo(21, 1);
    });

    test('contrast ratio: same color = 1:1', () => {
        const l = luminance(100, 100, 100);
        expect(contrastRatio(l, l)).toBeCloseTo(1, 6);
    });

    test('contrast ratio: symmetric (order of arguments does not matter)', () => {
        const l1 = luminance(232, 234, 237); // #E8EAED
        const l2 = luminance(18, 18, 18);    // #121212
        expect(contrastRatio(l1, l2)).toBeCloseTo(contrastRatio(l2, l1), 6);
    });

    // ── Verification 1: Primary text on primary background ──────────────────

    test('Verification 1: #E8EAED on #121212 ≥ 4.5:1 (primary text, normal size)', () => {
        // Requirement 1.7, 3.6: primary text must meet WCAG AA for normal text
        const ratio = hexContrastRatio(COLORS.TEXT_PRIMARY, COLORS.BG_PRIMARY);
        // Expected: ~15.54:1 — well above threshold
        expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    // ── Verification 2: Secondary text on primary background ────────────────

    test('Verification 2: #9AA0A6 on #121212 ≥ 4.5:1 (secondary text, normal size)', () => {
        // Requirement 1.7, 3.6: secondary text must meet WCAG AA for normal text
        const ratio = hexContrastRatio(COLORS.TEXT_SECONDARY, COLORS.BG_PRIMARY);
        // Expected: ~7.09:1 — above threshold
        expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    // ── Verification 3: Muted text on primary background (large text) ────────

    test('Verification 3: #5F6368 on #121212 ≥ 3:1 (muted text, large text only)', () => {
        // Requirement 1.7: muted text is used for large text (≥ 24px or ≥ 18.66px bold)
        // and UI component labels — WCAG AA large text threshold is 3:1
        const ratio = hexContrastRatio(COLORS.TEXT_MUTED, COLORS.BG_PRIMARY);
        // Expected: ~3.10:1 — just above threshold
        expect(ratio).toBeGreaterThanOrEqual(3.0);
    });

    // ── Verification 4: Google accent colors on bg-tertiary (#1e1e2e) ────────

    test('Verification 4a: #4285F4 (Google Blue) on #1e1e2e ≥ 3:1 (UI component)', () => {
        // Requirement 1.10: accent colors must meet 3:1 for UI components
        const ratio = hexContrastRatio(COLORS.ACCENT_BLUE, COLORS.BG_TERTIARY);
        // Expected: ~4.60:1
        expect(ratio).toBeGreaterThanOrEqual(3.0);
    });

    test('Verification 4b: #DB4437 (Google Red) on #1e1e2e ≥ 3:1 (UI component)', () => {
        // Requirement 1.10: accent colors must meet 3:1 for UI components
        const ratio = hexContrastRatio(COLORS.ACCENT_RED, COLORS.BG_TERTIARY);
        // Expected: ~3.82:1
        expect(ratio).toBeGreaterThanOrEqual(3.0);
    });

    test('Verification 4c: #0F9D58 (Google Green) on #1e1e2e ≥ 3:1 (UI component)', () => {
        // Requirement 1.10: accent colors must meet 3:1 for UI components
        const ratio = hexContrastRatio(COLORS.ACCENT_GREEN, COLORS.BG_TERTIARY);
        // Expected: ~4.67:1
        expect(ratio).toBeGreaterThanOrEqual(3.0);
    });

    test('Verification 4d: #F4B400 (Google Yellow) on #1e1e2e ≥ 3:1 (UI component)', () => {
        // Requirement 1.10: accent colors must meet 3:1 for UI components
        const ratio = hexContrastRatio(COLORS.ACCENT_YELLOW, COLORS.BG_TERTIARY);
        // Expected: ~8.88:1
        expect(ratio).toBeGreaterThanOrEqual(3.0);
    });

    // ── Property: all text tokens meet their respective thresholds ───────────

    test('Property: all text tokens meet WCAG AA thresholds against bg-primary', () => {
        /**
         * Validates: Requirements 1.7, 1.10, 3.6, 10.3
         *
         * For each text token, verify the contrast ratio against the primary
         * background meets the appropriate WCAG AA threshold:
         *   - Primary and secondary text: ≥ 4.5:1 (normal text)
         *   - Muted text: ≥ 3:1 (large text / UI components only)
         */
        const textTokens = [
            { color: COLORS.TEXT_PRIMARY,   threshold: 4.5, label: 'text-primary (#E8EAED)' },
            { color: COLORS.TEXT_SECONDARY, threshold: 4.5, label: 'text-secondary (#9AA0A6)' },
            { color: COLORS.TEXT_MUTED,     threshold: 3.0, label: 'text-muted (#5F6368, large text)' },
        ];

        for (const { color, threshold, label } of textTokens) {
            const ratio = hexContrastRatio(color, COLORS.BG_PRIMARY);
            expect(ratio, `${label} on ${COLORS.BG_PRIMARY}`).toBeGreaterThanOrEqual(threshold);
        }
    });

    test('Property: all Google accent colors meet WCAG AA 3:1 against bg-tertiary', () => {
        /**
         * Validates: Requirements 1.10, 10.3
         *
         * Google accent colors are used for UI components (buttons, badges,
         * active states) against the card surface (#1e1e2e). WCAG AA for
         * UI components and large text requires ≥ 3:1.
         */
        const accentColors = [
            { color: COLORS.ACCENT_BLUE,   label: 'accent-blue (#4285F4)' },
            { color: COLORS.ACCENT_RED,    label: 'accent-red (#DB4437)' },
            { color: COLORS.ACCENT_GREEN,  label: 'accent-green (#0F9D58)' },
            { color: COLORS.ACCENT_YELLOW, label: 'accent-yellow (#F4B400)' },
        ];

        for (const { color, label } of accentColors) {
            const ratio = hexContrastRatio(color, COLORS.BG_TERTIARY);
            expect(ratio, `${label} on ${COLORS.BG_TERTIARY}`).toBeGreaterThanOrEqual(3.0);
        }
    });

});

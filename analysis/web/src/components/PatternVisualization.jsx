import { ReferenceLine, ReferenceDot } from 'recharts';

/**
 * Pattern color schemes
 */
const PATTERN_COLORS = {
    bullish: {
        primary: '#10b981',      // Green
        secondary: '#34d399',
        accent: '#6ee7b7',
        target: '#22c55e',
    },
    bearish: {
        primary: '#ef4444',      // Red
        secondary: '#f87171',
        accent: '#fca5a5',
        target: '#dc2626',
    },
    neutral: {
        neckline: '#f59e0b',     // Amber
        support: '#3b82f6',       // Blue
        resistance: '#8b5cf6',    // Purple
    }
};

/**
 * Get pattern configuration based on pattern type
 */
export function getPatternConfig(patternType) {
    const configs = {
        head_shoulders: {
            name: 'Head & Shoulders',
            signal: 'bearish',
            description: 'This bearish reversal pattern suggests potential downside.',
            points: ['left_shoulder', 'head', 'right_shoulder'],
            lines: ['neckline', 'target_price'],
        },
        inverse_head_shoulders: {
            name: 'Inverse Head & Shoulders',
            signal: 'bullish',
            description: 'This bullish reversal pattern suggests potential upside.',
            points: ['left_shoulder', 'head', 'right_shoulder'],
            lines: ['neckline', 'target_price'],
        },
        double_top: {
            name: 'Double Top',
            signal: 'bearish',
            description: 'Two similar peaks indicate strong resistance and potential reversal.',
            points: ['first_peak', 'second_peak', 'trough'],
            lines: ['neckline', 'target_price'],
        },
        double_bottom: {
            name: 'Double Bottom',
            signal: 'bullish',
            description: 'Two similar troughs indicate strong support and potential reversal.',
            points: ['first_trough', 'second_trough', 'peak'],
            lines: ['neckline', 'target_price'],
        },
        triple_top: {
            name: 'Triple Top',
            signal: 'bearish',
            description: 'Three similar peaks show persistent resistance level.',
            points: ['first_peak', 'second_peak', 'third_peak'],
            lines: ['neckline', 'target_price'],
        },
        triple_bottom: {
            name: 'Triple Bottom',
            signal: 'bullish',
            description: 'Three similar troughs show persistent support level.',
            points: ['first_trough', 'second_trough', 'third_trough'],
            lines: ['neckline', 'target_price'],
        },
        ascending_triangle: {
            name: 'Ascending Triangle',
            signal: 'bullish',
            description: 'Flat resistance with rising support suggests bullish breakout.',
            points: [],
            lines: ['resistance', 'support_current', 'target_price'],
        },
        descending_triangle: {
            name: 'Descending Triangle',
            signal: 'bearish',
            description: 'Flat support with falling resistance suggests bearish breakdown.',
            points: [],
            lines: ['support', 'resistance_current', 'target_price'],
        },
        cup_and_handle: {
            name: 'Cup and Handle',
            signal: 'bullish',
            description: 'U-shaped consolidation followed by handle suggests bullish continuation.',
            points: ['cup_bottom'],
            lines: ['resistance', 'target_price'],
        },
        bullish_flag: {
            name: 'Bullish Flag',
            signal: 'bullish',
            description: 'Strong upward move followed by consolidation suggests continuation.',
            points: [],
            lines: ['pole_high', 'flag_high', 'flag_low', 'target_price'],
        },
        falling_wedge: {
            name: 'Falling Wedge',
            signal: 'bullish',
            description: 'Converging downward trendlines suggest bullish reversal.',
            points: [],
            lines: ['resistance_current', 'support_current', 'breakout_level', 'target_price'],
        },
    };
    return configs[patternType] || null;
}

/**
 * Render pattern reference dots on chart
 */
export function renderPatternDots(pattern) {
    if (!pattern?.detected) return null;

    const config = getPatternConfig(pattern.pattern_type);
    if (!config) return null;

    const colors = PATTERN_COLORS[config.signal];
    const dots = [];

    // Head & Shoulders / Inverse Head & Shoulders
    if (pattern.pattern_type === 'head_shoulders' || pattern.pattern_type === 'inverse_head_shoulders') {
        if (pattern.left_shoulder) {
            dots.push(
                <ReferenceDot
                    key="left_shoulder"
                    x={pattern.left_shoulder.date}
                    y={pattern.left_shoulder.price}
                    r={8}
                    fill={PATTERN_COLORS.neutral.neckline}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.head) {
            dots.push(
                <ReferenceDot
                    key="head"
                    x={pattern.head.date}
                    y={pattern.head.price}
                    r={10}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.right_shoulder) {
            dots.push(
                <ReferenceDot
                    key="right_shoulder"
                    x={pattern.right_shoulder.date}
                    y={pattern.right_shoulder.price}
                    r={8}
                    fill={PATTERN_COLORS.neutral.neckline}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
    }

    // Double Top
    if (pattern.pattern_type === 'double_top') {
        if (pattern.first_peak) {
            dots.push(
                <ReferenceDot
                    key="first_peak"
                    x={pattern.first_peak.date}
                    y={pattern.first_peak.price}
                    r={8}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.second_peak) {
            dots.push(
                <ReferenceDot
                    key="second_peak"
                    x={pattern.second_peak.date}
                    y={pattern.second_peak.price}
                    r={8}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.trough) {
            dots.push(
                <ReferenceDot
                    key="trough"
                    x={pattern.trough.date}
                    y={pattern.trough.price}
                    r={6}
                    fill={PATTERN_COLORS.neutral.support}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
    }

    // Double Bottom
    if (pattern.pattern_type === 'double_bottom') {
        if (pattern.first_trough) {
            dots.push(
                <ReferenceDot
                    key="first_trough"
                    x={pattern.first_trough.date}
                    y={pattern.first_trough.price}
                    r={8}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.second_trough) {
            dots.push(
                <ReferenceDot
                    key="second_trough"
                    x={pattern.second_trough.date}
                    y={pattern.second_trough.price}
                    r={8}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
        if (pattern.peak) {
            dots.push(
                <ReferenceDot
                    key="peak"
                    x={pattern.peak.date}
                    y={pattern.peak.price}
                    r={6}
                    fill={PATTERN_COLORS.neutral.resistance}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
    }

    // Triple Top
    if (pattern.pattern_type === 'triple_top') {
        ['first_peak', 'second_peak', 'third_peak'].forEach((key, idx) => {
            if (pattern[key]) {
                dots.push(
                    <ReferenceDot
                        key={key}
                        x={pattern[key].date}
                        y={pattern[key].price}
                        r={idx === 1 ? 9 : 7}
                        fill={colors.primary}
                        stroke="#fff"
                        strokeWidth={2}
                    />
                );
            }
        });
    }

    // Triple Bottom
    if (pattern.pattern_type === 'triple_bottom') {
        ['first_trough', 'second_trough', 'third_trough'].forEach((key, idx) => {
            if (pattern[key]) {
                dots.push(
                    <ReferenceDot
                        key={key}
                        x={pattern[key].date}
                        y={pattern[key].price}
                        r={idx === 1 ? 9 : 7}
                        fill={colors.primary}
                        stroke="#fff"
                        strokeWidth={2}
                    />
                );
            }
        });
    }

    // Cup and Handle - cup bottom marker
    if (pattern.pattern_type === 'cup_and_handle') {
        if (pattern.cup_bottom && pattern.cup_bottom_date) {
            dots.push(
                <ReferenceDot
                    key="cup_bottom"
                    x={pattern.cup_bottom_date}
                    y={pattern.cup_bottom}
                    r={8}
                    fill={colors.primary}
                    stroke="#fff"
                    strokeWidth={2}
                />
            );
        }
    }

    return dots;
}

/**
 * Render pattern reference lines on chart
 */
export function renderPatternLines(pattern) {
    if (!pattern?.detected) return null;

    const config = getPatternConfig(pattern.pattern_type);
    if (!config) return null;

    const colors = PATTERN_COLORS[config.signal];
    const lines = [];

    // Neckline (for H&S variants, Double/Triple patterns)
    if (pattern.neckline) {
        lines.push(
            <ReferenceLine
                key="neckline"
                y={pattern.neckline}
                stroke={PATTERN_COLORS.neutral.neckline}
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{ value: 'Neckline', fill: PATTERN_COLORS.neutral.neckline, fontSize: 11, position: 'right' }}
            />
        );
    }

    // Target price
    if (pattern.target_price) {
        lines.push(
            <ReferenceLine
                key="target"
                y={pattern.target_price}
                stroke={colors.target}
                strokeDasharray="3 3"
                strokeWidth={1}
                label={{ value: 'Target', fill: colors.target, fontSize: 10, position: 'right' }}
            />
        );
    }

    // Ascending Triangle - flat resistance, rising support shown as current level
    if (pattern.pattern_type === 'ascending_triangle') {
        if (pattern.resistance) {
            lines.push(
                <ReferenceLine
                    key="resistance"
                    y={pattern.resistance}
                    stroke={PATTERN_COLORS.neutral.resistance}
                    strokeWidth={2}
                    label={{ value: 'Resistance', fill: PATTERN_COLORS.neutral.resistance, fontSize: 10, position: 'right' }}
                />
            );
        }
        if (pattern.support_current) {
            lines.push(
                <ReferenceLine
                    key="support"
                    y={pattern.support_current}
                    stroke={PATTERN_COLORS.neutral.support}
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{ value: 'Support', fill: PATTERN_COLORS.neutral.support, fontSize: 10, position: 'right' }}
                />
            );
        }
    }

    // Descending Triangle - flat support, falling resistance
    if (pattern.pattern_type === 'descending_triangle') {
        if (pattern.support) {
            lines.push(
                <ReferenceLine
                    key="support"
                    y={pattern.support}
                    stroke={PATTERN_COLORS.neutral.support}
                    strokeWidth={2}
                    label={{ value: 'Support', fill: PATTERN_COLORS.neutral.support, fontSize: 10, position: 'right' }}
                />
            );
        }
        if (pattern.resistance_current) {
            lines.push(
                <ReferenceLine
                    key="resistance"
                    y={pattern.resistance_current}
                    stroke={PATTERN_COLORS.neutral.resistance}
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{ value: 'Resistance', fill: PATTERN_COLORS.neutral.resistance, fontSize: 10, position: 'right' }}
                />
            );
        }
    }

    // Cup and Handle - resistance level
    if (pattern.pattern_type === 'cup_and_handle') {
        if (pattern.resistance) {
            lines.push(
                <ReferenceLine
                    key="resistance"
                    y={pattern.resistance}
                    stroke={PATTERN_COLORS.neutral.resistance}
                    strokeDasharray="5 5"
                    strokeWidth={2}
                    label={{ value: 'Resistance', fill: PATTERN_COLORS.neutral.resistance, fontSize: 10, position: 'right' }}
                />
            );
        }
    }

    // Bullish Flag - pole high and flag channel
    if (pattern.pattern_type === 'bullish_flag') {
        if (pattern.pole_high) {
            lines.push(
                <ReferenceLine
                    key="pole_high"
                    y={pattern.pole_high}
                    stroke={PATTERN_COLORS.neutral.resistance}
                    strokeDasharray="5 5"
                    strokeWidth={2}
                    label={{ value: 'Pole High', fill: PATTERN_COLORS.neutral.resistance, fontSize: 10, position: 'right' }}
                />
            );
        }
        if (pattern.flag_high) {
            lines.push(
                <ReferenceLine
                    key="flag_high"
                    y={pattern.flag_high}
                    stroke={colors.secondary}
                    strokeDasharray="3 3"
                    strokeWidth={1}
                    label={{ value: 'Flag', fill: colors.secondary, fontSize: 9, position: 'right' }}
                />
            );
        }
        if (pattern.flag_low) {
            lines.push(
                <ReferenceLine
                    key="flag_low"
                    y={pattern.flag_low}
                    stroke={colors.secondary}
                    strokeDasharray="3 3"
                    strokeWidth={1}
                />
            );
        }
    }

    // Falling Wedge - converging lines
    if (pattern.pattern_type === 'falling_wedge') {
        if (pattern.resistance_current) {
            lines.push(
                <ReferenceLine
                    key="resistance"
                    y={pattern.resistance_current}
                    stroke={PATTERN_COLORS.neutral.resistance}
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{ value: 'Resistance', fill: PATTERN_COLORS.neutral.resistance, fontSize: 10, position: 'right' }}
                />
            );
        }
        if (pattern.support_current) {
            lines.push(
                <ReferenceLine
                    key="support"
                    y={pattern.support_current}
                    stroke={PATTERN_COLORS.neutral.support}
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    label={{ value: 'Support', fill: PATTERN_COLORS.neutral.support, fontSize: 10, position: 'right' }}
                />
            );
        }
        if (pattern.breakout_level) {
            lines.push(
                <ReferenceLine
                    key="breakout"
                    y={pattern.breakout_level}
                    stroke={colors.primary}
                    strokeWidth={2}
                    label={{ value: 'Breakout', fill: colors.primary, fontSize: 10, position: 'right' }}
                />
            );
        }
    }

    return lines;
}

/**
 * Get legend items for a pattern
 */
export function getPatternLegend(pattern) {
    if (!pattern?.detected) return [];

    const config = getPatternConfig(pattern.pattern_type);
    if (!config) return [];

    const colors = PATTERN_COLORS[config.signal];
    const legend = [];

    // Pattern-specific legend items
    switch (pattern.pattern_type) {
        case 'head_shoulders':
        case 'inverse_head_shoulders':
            legend.push(
                { type: 'dot', color: colors.primary, label: config.signal === 'bullish' ? 'Head (Low)' : 'Head' },
                { type: 'dot', color: PATTERN_COLORS.neutral.neckline, label: 'Shoulders' },
                { type: 'line', color: PATTERN_COLORS.neutral.neckline, dashed: true, label: 'Neckline' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'double_top':
            legend.push(
                { type: 'dot', color: colors.primary, label: 'Peaks' },
                { type: 'dot', color: PATTERN_COLORS.neutral.support, label: 'Trough' },
                { type: 'line', color: PATTERN_COLORS.neutral.neckline, dashed: true, label: 'Neckline' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'double_bottom':
            legend.push(
                { type: 'dot', color: colors.primary, label: 'Troughs' },
                { type: 'dot', color: PATTERN_COLORS.neutral.resistance, label: 'Peak' },
                { type: 'line', color: PATTERN_COLORS.neutral.neckline, dashed: true, label: 'Neckline' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'triple_top':
            legend.push(
                { type: 'dot', color: colors.primary, label: 'Peaks' },
                { type: 'line', color: PATTERN_COLORS.neutral.neckline, dashed: true, label: 'Neckline' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'triple_bottom':
            legend.push(
                { type: 'dot', color: colors.primary, label: 'Troughs' },
                { type: 'line', color: PATTERN_COLORS.neutral.neckline, dashed: true, label: 'Neckline' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'ascending_triangle':
            legend.push(
                { type: 'line', color: PATTERN_COLORS.neutral.resistance, dashed: false, label: 'Resistance' },
                { type: 'line', color: PATTERN_COLORS.neutral.support, dashed: true, label: 'Support' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'descending_triangle':
            legend.push(
                { type: 'line', color: PATTERN_COLORS.neutral.support, dashed: false, label: 'Support' },
                { type: 'line', color: PATTERN_COLORS.neutral.resistance, dashed: true, label: 'Resistance' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'cup_and_handle':
            legend.push(
                { type: 'dot', color: colors.primary, label: 'Cup Bottom' },
                { type: 'line', color: PATTERN_COLORS.neutral.resistance, dashed: true, label: 'Resistance' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'bullish_flag':
            legend.push(
                { type: 'line', color: PATTERN_COLORS.neutral.resistance, dashed: true, label: 'Pole High' },
                { type: 'line', color: colors.secondary, dashed: true, label: 'Flag Channel' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        case 'falling_wedge':
            legend.push(
                { type: 'line', color: PATTERN_COLORS.neutral.resistance, dashed: true, label: 'Resistance' },
                { type: 'line', color: PATTERN_COLORS.neutral.support, dashed: true, label: 'Support' },
                { type: 'line', color: colors.primary, dashed: false, label: 'Breakout' },
                { type: 'line', color: colors.target, dashed: true, label: 'Target' }
            );
            break;
        default:
            break;
    }

    return legend;
}

export { PATTERN_COLORS };

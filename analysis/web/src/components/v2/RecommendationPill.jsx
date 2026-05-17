import React from 'react';

const REC_COLORS = {
    BUY: 'green', HOLD: 'yellow', TRIM: 'orange', AVOID: 'red',
};
const CONV_COLORS = { HIGH: 'green', MEDIUM: 'yellow', LOW: 'gray' };

/**
 * Large recommendation pill with conviction stripe.
 * @param {{ recommendation: string, conviction: string, small?: boolean }} props
 */
export default function RecommendationPill({ recommendation, conviction, small = false }) {
    const rec = (recommendation || 'HOLD').toUpperCase();
    const conv = (conviction || 'LOW').toUpperCase();
    const recColor = REC_COLORS[rec] || 'gray';
    const convColor = CONV_COLORS[conv] || 'gray';

    if (small) {
        return (
            <span className={`badge badge-${recColor}`} style={{ fontSize: '0.7rem', padding: '3px 10px', fontWeight: 700 }}>
                {rec}
            </span>
        );
    }

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className={`badge badge-${recColor}`} style={{
                fontSize: '1.1rem', padding: '8px 20px', fontWeight: 700,
                letterSpacing: '0.04em',
            }}>
                {rec}
            </span>
            <span className={`badge badge-${convColor}`} style={{
                fontSize: '0.75rem', padding: '4px 12px',
                border: '1px solid', fontWeight: 600,
            }}>
                {conv} conviction
            </span>
        </div>
    );
}

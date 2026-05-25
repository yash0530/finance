import React from 'react';

/**
 * Compact horizontal stage timeline for the deep research pipeline.
 * Maps SSE events to stages with checkmarks / spinner / pending dots.
 */

const STAGES = [
    { key: 'context', label: 'Context' },
    { key: 'plan', label: 'Plan' },
    { key: 'tools', label: 'Tools' },
    { key: 'bull', label: 'Bull' },
    { key: 'bear', label: 'Bear' },
    { key: 'judge', label: 'Judge' },
    { key: 'critique', label: 'Critique' },
    { key: 'memo', label: 'Memo' },
    { key: 'done', label: 'Done' },
];

/**
 * @param {{ stageStatuses: Record<string, 'pending'|'active'|'complete'|'error'>, toolProgress?: string }} props
 */
export default function StageTimeline({ stageStatuses = {}, toolProgress }) {
    const completedCount = STAGES.filter(s => stageStatuses[s.key] === 'complete').length;
    const progressPct = STAGES.length > 0 ? (completedCount / STAGES.length) * 100 : 0;

    return (
        <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            {/* Progress bar */}
            <div style={{
                height: 3, background: 'var(--bg-tertiary)', borderRadius: 2,
                marginBottom: 12, overflow: 'hidden',
            }}>
                <div style={{
                    height: '100%', background: 'var(--gradient-green)',
                    width: `${progressPct}%`, transition: 'width 0.4s ease',
                }} />
            </div>

            {/* Stage pills */}
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                {STAGES.map((stage, i) => {
                    const status = stageStatuses[stage.key] || 'pending';
                    return (
                        <React.Fragment key={stage.key}>
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: 4,
                                padding: '4px 10px', borderRadius: 'var(--radius-pill)',
                                background: status === 'complete' ? 'rgba(16, 217, 160, 0.12)'
                                    : status === 'active' ? 'rgba(45, 126, 247, 0.12)'
                                    : status === 'error' ? 'rgba(244, 63, 94, 0.12)'
                                    : 'var(--bg-secondary)',
                                border: `1px solid ${
                                    status === 'complete' ? 'rgba(16, 217, 160, 0.3)'
                                    : status === 'active' ? 'rgba(45, 126, 247, 0.3)'
                                    : status === 'error' ? 'rgba(244, 63, 94, 0.3)'
                                    : 'var(--border-color)'
                                }`,
                                transition: 'all 0.3s ease',
                            }}>
                                {status === 'active' && <span className="spinner spinner-sm" style={{ width: 10, height: 10 }} />}
                                {status === 'complete' && <span style={{ fontSize: '0.7rem', color: 'var(--accent-green)' }}>✓</span>}
                                {status === 'error' && <span style={{ fontSize: '0.7rem', color: 'var(--accent-red)' }}>!</span>}
                                {status === 'pending' && <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>○</span>}
                                <span style={{
                                    fontSize: '0.68rem', fontWeight: 500,
                                    color: status === 'complete' ? 'var(--accent-green)'
                                        : status === 'active' ? 'var(--accent-blue-bright)'
                                        : status === 'error' ? 'var(--accent-red)'
                                        : 'var(--text-muted)',
                                }}>
                                    {stage.label}
                                </span>
                                {stage.key === 'tools' && toolProgress && status === 'active' && (
                                    <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>({toolProgress})</span>
                                )}
                            </div>
                            {i < STAGES.length - 1 && (
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.6rem' }}>→</span>
                            )}
                        </React.Fragment>
                    );
                })}
            </div>
        </div>
    );
}

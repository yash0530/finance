import { useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = [
    '#2d7ef7', '#10d9a0', '#f59e0b', '#ec4899', '#7c3aed',
    '#06d6f0', '#f43f5e', '#14b8a6', '#6366f1', '#f97316', '#a855f7',
];

const RADIAN = Math.PI / 180;

function CustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
    if (percent < 0.04) return null;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
        <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
            style={{ fontSize: '0.65rem', fontWeight: 600 }}>
            {`${(percent * 100).toFixed(0)}%`}
        </text>
    );
}

function CustomTooltip({ active, payload }) {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
        <div style={{
            background: '#1e1e2e', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 8, padding: '8px 12px', fontSize: '0.8rem'
        }}>
            <div style={{ fontWeight: 700, color: payload[0].fill }}>{d.ticker}</div>
            <div style={{ color: 'var(--text-secondary)' }}>
                ${d.current_value?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—'}
            </div>
            <div style={{ color: 'var(--text-muted)' }}>{d.weight_pct?.toFixed(1)}%</div>
        </div>
    );
}

export default function AllocationChart({ holdings }) {
    const data = (holdings || [])
        .filter(h => h.current_value && h.weight_pct)
        .sort((a, b) => b.current_value - a.current_value);

    if (!data.length) return (
        <div className="empty-state" style={{ padding: 'var(--spacing-xl)' }}>
            <div className="empty-state-icon">📊</div>
            <p>No allocation data</p>
        </div>
    );

    return (
        <ResponsiveContainer width="100%" height={320}>
            <PieChart>
                <Pie
                    data={data}
                    dataKey="current_value"
                    nameKey="ticker"
                    cx="50%" cy="45%"
                    innerRadius={65}
                    outerRadius={110}
                    paddingAngle={2}
                    labelLine={false}
                    label={CustomLabel}
                >
                    {data.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                    formatter={(value, entry) => (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            {entry.payload.ticker}
                        </span>
                    )}
                    iconSize={8}
                />
            </PieChart>
        </ResponsiveContainer>
    );
}

import { BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { formatCurrency } from '../utils/api';

// ── Trend Direction Arrow ─────────────────────────────────
function TrendArrow({ direction }) {
    const config = {
        expanding:            { arrow: '↑', color: 'var(--accent-green)',  label: 'Expanding' },
        slightly_expanding:   { arrow: '↗', color: 'var(--accent-green)',  label: 'Slight expansion' },
        stable:               { arrow: '→', color: 'var(--accent-yellow)', label: 'Stable' },
        slightly_contracting: { arrow: '↘', color: 'var(--accent-red)',    label: 'Slight contraction' },
        contracting:          { arrow: '↓', color: 'var(--accent-red)',    label: 'Contracting' },
        insufficient_data:    { arrow: '—', color: 'var(--text-muted)',    label: 'Insufficient data' },
    };
    const c = config[direction] || config.insufficient_data;
    return (
        <span style={{ color: c.color, fontWeight: 700, fontSize: '0.75rem' }} title={c.label}>
            {c.arrow} {c.label}
        </span>
    );
}

// ── Custom Tooltip ────────────────────────────────────────
function ChartTooltip({ active, payload, label, formatter }) {
    if (!active || !payload?.length) return null;
    return (
        <div style={{
            background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)',
            borderRadius: 8, padding: '8px 12px', fontSize: '0.75rem',
        }}>
            <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color || 'var(--text-primary)' }}>
                    {p.name}: {formatter ? formatter(p.value) : p.value?.toLocaleString()}
                </div>
            ))}
        </div>
    );
}

// ── Signal Badge ──────────────────────────────────────────
function SignalBadge({ label, value, verdict }) {
    const cls = verdict === 'high' || verdict === 'accelerating' || verdict === 'expanding'
        ? 'badge-green'
        : verdict === 'low' || verdict === 'decelerating' || verdict === 'contracting'
            ? 'badge-red'
            : 'badge-yellow';
    return (
        <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 10px', background: 'var(--bg-secondary)', borderRadius: 8,
        }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{label}</span>
            <span className={`badge ${cls}`} style={{ fontSize: '0.65rem' }}>{value}</span>
        </div>
    );
}


// ── Main Component ────────────────────────────────────────
export default function FinancialTrendsChart({ trends }) {
    if (!trends || !trends.quarters?.length) {
        return (
            <div className="glass-card">
                <div className="empty-state" style={{ padding: 'var(--spacing-md)' }}>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        No quarterly financial data available for this ticker
                    </p>
                </div>
            </div>
        );
    }

    const { quarters, signals } = trends;
    const fmtQ = quarters.map(q => ({
        ...q,
        label: q.quarter_label,
        rev_m: q.revenue ? +(q.revenue / 1e6).toFixed(0) : null,
        fcf_m: q.fcf ? +(q.fcf / 1e6).toFixed(0) : null,
        ni_m: q.net_income ? +(q.net_income / 1e6).toFixed(0) : null,
    }));

    return (
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
            <div className="card-header" style={{ marginBottom: 0 }}>
                <span className="card-title">📈 Financial Trajectory ({quarters.length} Quarters)</span>
            </div>

            {/* Trend Signals Summary */}
            {signals && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                    <SignalBadge
                        label="Revenue Growth"
                        value={signals.revenue_acceleration || '—'}
                        verdict={signals.revenue_acceleration}
                    />
                    <SignalBadge
                        label="Gross Margin"
                        value={signals.gross_margin_trend?.direction || '—'}
                        verdict={signals.gross_margin_trend?.direction}
                    />
                    <SignalBadge
                        label="Earnings Quality"
                        value={signals.earnings_quality_verdict || '—'}
                        verdict={signals.earnings_quality_verdict}
                    />
                </div>
            )}

            {/* Revenue Bar Chart */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                        Revenue ($M)
                    </span>
                    {signals?.revenue_trend && <TrendArrow direction={signals.revenue_trend.direction} />}
                </div>
                <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={fmtQ} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,126,247,0.08)" />
                        <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                        <Tooltip content={<ChartTooltip formatter={v => `$${v?.toLocaleString()}M`} />} />
                        <Bar dataKey="rev_m" name="Revenue" fill="var(--accent-blue)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Margin Trends Line Chart */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                        Margin Trends (%)
                    </span>
                    {signals?.net_margin_trend && <TrendArrow direction={signals.net_margin_trend.direction} />}
                </div>
                <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={fmtQ} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,126,247,0.08)" />
                        <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                        <Tooltip content={<ChartTooltip formatter={v => `${v?.toFixed(1)}%`} />} />
                        <Line type="monotone" dataKey="gross_margin" name="Gross" stroke="var(--accent-green)" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="operating_margin" name="Operating" stroke="var(--accent-blue)" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="net_margin" name="Net" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
                    </LineChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 4 }}>
                    {[
                        { label: 'Gross', color: 'var(--accent-green)' },
                        { label: 'Operating', color: 'var(--accent-blue)' },
                        { label: 'Net', color: 'var(--accent-cyan)' },
                    ].map(l => (
                        <span key={l.label} style={{ fontSize: '0.65rem', color: l.color, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 10, height: 2, background: l.color, borderRadius: 1 }} />
                            {l.label}
                        </span>
                    ))}
                </div>
            </div>

            {/* FCF Area Chart */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                        Free Cash Flow ($M)
                    </span>
                    {signals?.fcf_trend && <TrendArrow direction={signals.fcf_trend.direction} />}
                </div>
                <ResponsiveContainer width="100%" height={120}>
                    <AreaChart data={fmtQ} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,126,247,0.08)" />
                        <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                        <Tooltip content={<ChartTooltip formatter={v => `$${v?.toLocaleString()}M`} />} />
                        <defs>
                            <linearGradient id="fcfGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--accent-purple)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--accent-purple)" stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <Area type="monotone" dataKey="fcf_m" name="FCF" stroke="var(--accent-purple)" fill="url(#fcfGrad)" strokeWidth={2} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Additional metrics row */}
            {signals && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                    <SignalBadge
                        label="FCF Trend"
                        value={signals.fcf_trend?.direction || '—'}
                        verdict={signals.fcf_trend?.direction}
                    />
                    <SignalBadge
                        label="ROE Trend"
                        value={signals.roe_trend?.direction || '—'}
                        verdict={signals.roe_trend?.direction}
                    />
                    <SignalBadge
                        label="Debt/Equity"
                        value={signals.debt_equity_trend?.direction || '—'}
                        verdict={signals.debt_equity_trend?.direction === 'contracting' ? 'expanding' : signals.debt_equity_trend?.direction === 'expanding' ? 'contracting' : signals.debt_equity_trend?.direction}
                    />
                </div>
            )}
        </div>
    );
}

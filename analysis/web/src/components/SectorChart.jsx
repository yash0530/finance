import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { getSectorColor } from '../utils/api';
import './SectorChart.css';

function SectorChart({ sectors }) {
    if (!sectors || sectors.length === 0) return null;

    // Prepare data for charts
    const pieData = sectors.map(s => ({
        name: s.name,
        value: s.total_market_cap,
        color: getSectorColor(s.name)
    }));

    const barData = sectors
        .filter(s => s.avg_forward_pe && s.avg_forward_pe > 0)
        .sort((a, b) => a.avg_forward_pe - b.avg_forward_pe)
        .map(s => ({
            name: s.name.length > 15 ? s.name.substring(0, 15) + '...' : s.name,
            fullName: s.name,
            avg_pe: s.avg_forward_pe,
            median_pe: s.median_forward_pe,
            color: getSectorColor(s.name)
        }));

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="chart-tooltip">
                    <p className="tooltip-label">{data.fullName || data.name}</p>
                    {payload.map((p, i) => (
                        <p key={i} className="tooltip-value" style={{ color: p.color }}>
                            {p.name}: {p.value?.toFixed(2)}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    const formatMarketCap = (value) => {
        if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
        if (value >= 1e9) return `$${(value / 1e9).toFixed(0)}B`;
        return `$${value}`;
    };

    return (
        <section className="charts-section fade-in">
            <h2 className="section-title">Market Analysis</h2>

            <div className="charts-grid">
                {/* Market Cap Distribution Pie Chart */}
                <div className="chart-card glass-card">
                    <h3>Market Cap by Sector</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={pieData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={100}
                                paddingAngle={2}
                                dataKey="value"
                                label={({ name, percent }) =>
                                    percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''
                                }
                                labelLine={false}
                            >
                                {pieData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip
                                formatter={(value) => formatMarketCap(value)}
                                contentStyle={{
                                    background: 'var(--bg-secondary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: 'var(--radius-sm)'
                                }}
                            />
                            <Legend
                                layout="vertical"
                                align="right"
                                verticalAlign="middle"
                                formatter={(value) => <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{value}</span>}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* P/E Ratio Bar Chart */}
                <div className="chart-card glass-card">
                    <h3>Average Forward P/E by Sector</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={barData} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                            <XAxis
                                type="number"
                                stroke="var(--text-muted)"
                                tickFormatter={(v) => v.toFixed(0)}
                            />
                            <YAxis
                                type="category"
                                dataKey="name"
                                stroke="var(--text-muted)"
                                width={120}
                                tick={{ fontSize: 11 }}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="avg_pe" name="Avg P/E" radius={[0, 4, 4, 0]}>
                                {barData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </section>
    );
}

export default SectorChart;

import { useState, useEffect, useCallback } from 'react';
import {
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { getChart } from '../../utils/api';

const RANGES = ['1d', '5d', '1m', '3m', '1y', '5y'];

export default function StockChart({ ticker }) {
    const [range, setRange] = useState('1y');
    const [bars, setBars] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const res = await getChart(ticker, range);
            setBars(res.data?.bars || []);
            if (res.error && !(res.data?.bars?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker, range]);

    useEffect(() => { load(); }, [load]);

    const chartData = bars.map(b => ({
        time: b.time.slice(0, 10),
        close: b.close,
    }));

    const up = chartData.length >= 2 && chartData[chartData.length - 1].close >= chartData[0].close;
    const color = up ? 'var(--accent-green)' : 'var(--accent-red)';

    return (
        <div className="glass-card" id="stock-chart" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-sm)' }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 700, margin: 0 }}>Price</h3>
                <div style={{ display: 'flex', gap: 4 }}>
                    {RANGES.map(r => (
                        <button
                            key={r}
                            className={`btn ${r === range ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ fontSize: '0.68rem', padding: '2px 8px' }}
                            onClick={() => setRange(r)}
                        >{r}</button>
                    ))}
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ fontSize: '0.72rem' }}>{error}</div>}
            {loading && <div className="loading-state" style={{ minHeight: 200 }}><div className="spinner" /></div>}

            {!loading && chartData.length > 0 && (
                <ResponsiveContainer width="100%" height={320}>
                    <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                        <defs>
                            <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={color} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} minTickGap={40} />
                        <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} width={48} />
                        <Tooltip
                            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', fontSize: '0.72rem' }}
                            labelStyle={{ color: 'var(--text-muted)' }}
                        />
                        <Area type="monotone" dataKey="close" stroke={color} strokeWidth={1.5} fill="url(#chartFill)" />
                    </AreaChart>
                </ResponsiveContainer>
            )}

            {!loading && chartData.length === 0 && !error && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: 'var(--spacing-md)' }}>No price data.</div>
            )}
        </div>
    );
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import { getChart } from '../../utils/api';

const RANGES = ['1d', '5d', '1m', '3m', '1y', '5y'];
const OVERLAYS = [
    { key: 'ma20', label: 'MA20', color: '#5a9cf6' },
    { key: 'ma50', label: 'MA50', color: '#AB47BC' },
    { key: 'bb', label: 'BB', color: '#F4B400' },
    { key: 'vwap', label: 'VWAP', color: '#80deea' },
];

function toUnixTime(iso) {
    return Math.floor(new Date(iso).getTime() / 1000);
}

/**
 * Candlestick chart (lightweight-charts) with server-computed overlays.
 *
 * Overlay toggles don't re-fetch — the overlay series are cached alongside the
 * bars per range and added/removed from the existing chart instance.
 */
export default function StockChart({ ticker }) {
    const [range, setRange] = useState('1y');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [active, setActive] = useState({ ma20: false, ma50: true, bb: false, vwap: false });

    const containerRef = useRef(null);
    const chartRef = useRef(null);
    const candleRef = useRef(null);
    const overlaySeriesRef = useRef({});

    const load = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const res = await getChart(ticker, range);
            setData(res.data);
            if (res.error && !(res.data?.bars?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [ticker, range]);

    useEffect(() => { load(); }, [load]);

    // Create the chart once.
    useEffect(() => {
        if (!containerRef.current || chartRef.current) return;
        const chart = createChart(containerRef.current, {
            height: 340,
            layout: { background: { color: 'transparent' }, textColor: '#9AA0A6' },
            grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
            crosshair: { mode: CrosshairMode.Normal },
            rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
            timeScale: { borderColor: 'rgba(255,255,255,0.1)', timeVisible: true },
        });
        const candle = chart.addCandlestickSeries({
            upColor: '#0F9D58', downColor: '#DB4437',
            borderUpColor: '#0F9D58', borderDownColor: '#DB4437',
            wickUpColor: '#0F9D58', wickDownColor: '#DB4437',
        });
        chartRef.current = chart;
        candleRef.current = candle;

        const onResize = () => chart.applyOptions({ width: containerRef.current?.clientWidth });
        onResize();
        window.addEventListener('resize', onResize);
        return () => {
            window.removeEventListener('resize', onResize);
            chart.remove();
            chartRef.current = null;
            candleRef.current = null;
            overlaySeriesRef.current = {};
        };
    }, []);

    // Push candle data when bars change.
    useEffect(() => {
        if (!candleRef.current || !data?.bars) return;
        const candles = data.bars.map(b => ({
            time: toUnixTime(b.time),
            open: b.open, high: b.high, low: b.low, close: b.close,
        }));
        candleRef.current.setData(candles);
        chartRef.current?.timeScale().fitContent();
    }, [data]);

    // Sync overlay line series with the active toggles + data.
    useEffect(() => {
        const chart = chartRef.current;
        if (!chart || !data?.bars) return;
        const overlays = data.overlays || {};
        const bars = data.bars;
        const series = overlaySeriesRef.current;

        const ensure = (id, color) => {
            if (!series[id]) {
                series[id] = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
            }
            return series[id];
        };
        const drop = (id) => {
            if (series[id]) { chart.removeSeries(series[id]); delete series[id]; }
        };
        const lineData = (arr) => bars
            .map((b, i) => ({ time: toUnixTime(b.time), value: arr?.[i] }))
            .filter(p => p.value != null);

        // MA20 / MA50 / VWAP — single line each
        for (const [id, arrKey, color] of [['ma20', 'ma20', '#5a9cf6'], ['ma50', 'ma50', '#AB47BC'], ['vwap', 'vwap', '#80deea']]) {
            if (active[id] && overlays[arrKey]) ensure(id, color).setData(lineData(overlays[arrKey]));
            else drop(id);
        }
        // Bollinger — upper + lower
        if (active.bb && overlays.bb_upper && overlays.bb_lower) {
            ensure('bb_upper', 'rgba(244,180,0,0.6)').setData(lineData(overlays.bb_upper));
            ensure('bb_lower', 'rgba(244,180,0,0.6)').setData(lineData(overlays.bb_lower));
        } else {
            drop('bb_upper'); drop('bb_lower');
        }
    }, [active, data]);

    return (
        <div className="glass-card" id="stock-chart" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-sm)', flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', gap: 4 }}>
                    {OVERLAYS.map(o => (
                        <button
                            key={o.key}
                            className={`btn ${active[o.key] ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ fontSize: '0.66rem', padding: '2px 7px' }}
                            onClick={() => setActive(a => ({ ...a, [o.key]: !a[o.key] }))}
                        >{o.label}</button>
                    ))}
                </div>
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
            <div ref={containerRef} style={{ width: '100%', position: 'relative' }}>
                {loading && (
                    <div className="loading-state" style={{ position: 'absolute', inset: 0, zIndex: 2 }}><div className="spinner" /></div>
                )}
            </div>
        </div>
    );
}

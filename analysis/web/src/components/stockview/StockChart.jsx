import { useCallback, useEffect, useMemo, useState } from 'react';
import { getChart, formatNumber, formatPercent } from '../../utils/api';

const RANGES = ['1d', '5d', '1m', '3m', '6m', 'YTD', '1y', '5y'];
const RANGE_MAP = { '6m': '1y', YTD: '1y' };
const OVERLAYS = [
    { key: 'ma20', label: 'MA20', color: '#5a9cf6' },
    { key: 'ma50', label: 'MA50', color: '#ab47bc' },
    { key: 'bb', label: 'BB', color: '#f4b400' },
    { key: 'vwap', label: 'VWAP', color: '#80deea' },
];

const CHART = {
    width: 1200,
    mainHeight: 460,
    rsiHeight: 128,
    macdHeight: 146,
    left: 24,
    right: 78,
    top: 22,
    bottom: 82,
};

function lastNumber(values = []) {
    for (let i = values.length - 1; i >= 0; i -= 1) {
        const value = values[i];
        if (value != null && Number.isFinite(Number(value))) return Number(value);
    }
    return null;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function formatDate(value, dense = false) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString(undefined, dense
        ? { month: 'short', day: 'numeric' }
        : { month: 'short', day: 'numeric', year: '2-digit' });
}

function filterBars(rawBars = [], range) {
    if (!rawBars.length || !['6m', 'YTD'].includes(range)) return rawBars;
    const now = new Date(rawBars[rawBars.length - 1].time);
    const cutoff = range === 'YTD'
        ? new Date(now.getFullYear(), 0, 1)
        : new Date(now.getTime() - 183 * 24 * 60 * 60 * 1000);
    return rawBars.filter(bar => new Date(bar.time) >= cutoff);
}

function sliceAligned(values = [], rawBars = [], visibleBars = []) {
    if (!rawBars.length || rawBars.length === visibleBars.length) return values || [];
    const firstTime = visibleBars[0]?.time;
    const start = rawBars.findIndex(bar => bar.time === firstTime);
    return start >= 0 ? (values || []).slice(start, start + visibleBars.length) : (values || []);
}

function makeScale(min, max, lowPx, highPx) {
    const span = max - min || 1;
    return value => highPx - ((Number(value) - min) / span) * (highPx - lowPx);
}

function linePath(values, bars, xFor, yFor) {
    let path = '';
    values.forEach((value, index) => {
        if (value == null || !Number.isFinite(Number(value))) return;
        const cmd = path ? 'L' : 'M';
        path += `${cmd}${xFor(index).toFixed(2)},${yFor(value).toFixed(2)}`;
    });
    return bars.length ? path : '';
}

function areaPath(upper = [], lower = [], bars, xFor, yFor) {
    const top = [];
    const bottom = [];
    upper.forEach((value, index) => {
        const lowerValue = lower[index];
        if (value == null || lowerValue == null) return;
        top.push(`${xFor(index).toFixed(2)},${yFor(value).toFixed(2)}`);
        bottom.unshift(`${xFor(index).toFixed(2)},${yFor(lowerValue).toFixed(2)}`);
    });
    if (!top.length || !bottom.length) return '';
    return `M${top.join('L')}L${bottom.join('L')}Z`;
}

function axisTicks(min, max, count = 5) {
    if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
    if (min === max) return [min];
    return Array.from({ length: count }, (_, index) => min + ((max - min) * index) / (count - 1));
}

function MiniStat({ label, value, tone = '' }) {
    return (
        <div className="stock-chart-stat">
            <span>{label}</span>
            <strong className={tone}>{value}</strong>
        </div>
    );
}

function ChartGrid({ width, height, top, bottom, left, right, yTicks, yFor, formatY, bars, xFor }) {
    const plotBottom = height - bottom;
    const dateSteps = bars.length > 1
        ? Array.from(new Set([0, Math.floor(bars.length * 0.25), Math.floor(bars.length * 0.5), Math.floor(bars.length * 0.75), bars.length - 1]))
        : [];
    return (
        <g className="native-chart-grid">
            {yTicks.map(tick => {
                const y = yFor(tick);
                return (
                    <g key={`y-${tick}`}>
                        <line x1={left} x2={width - right} y1={y} y2={y} />
                        <text x={width - right + 12} y={y + 4}>{formatY(tick)}</text>
                    </g>
                );
            })}
            {dateSteps.map(index => {
                const x = xFor(index);
                return (
                    <g key={`x-${index}`}>
                        <line x1={x} x2={x} y1={top} y2={plotBottom} />
                        <text x={x} y={height - 12} textAnchor="middle">{formatDate(bars[index].time, true)}</text>
                    </g>
                );
            })}
        </g>
    );
}

function NativePriceChart({ bars, overlays, active, hoverIndex, setHoverIndex }) {
    const { width, mainHeight: height, left, right, top, bottom } = CHART;
    const plotBottom = height - bottom;
    const volumeTop = height - 72;
    const volumeBottom = height - 22;
    const plotWidth = width - left - right;
    const candleWidth = clamp((plotWidth / Math.max(bars.length, 1)) * 0.6, 3, 12);
    const xFor = index => left + (bars.length <= 1 ? plotWidth / 2 : (index / (bars.length - 1)) * plotWidth);

    const priceValues = [];
    bars.forEach(bar => {
        priceValues.push(Number(bar.high), Number(bar.low));
    });
    if (active.ma20) priceValues.push(...(overlays.ma20 || []).filter(Boolean).map(Number));
    if (active.ma50) priceValues.push(...(overlays.ma50 || []).filter(Boolean).map(Number));
    if (active.vwap) priceValues.push(...(overlays.vwap || []).filter(Boolean).map(Number));
    if (active.bb) {
        priceValues.push(...(overlays.bb_upper || []).filter(Boolean).map(Number));
        priceValues.push(...(overlays.bb_lower || []).filter(Boolean).map(Number));
    }

    const rawMin = Math.min(...priceValues);
    const rawMax = Math.max(...priceValues);
    const padding = (rawMax - rawMin || rawMax || 1) * 0.08;
    const min = rawMin - padding;
    const max = rawMax + padding;
    const yFor = makeScale(min, max, top, plotBottom);
    const vMax = Math.max(...bars.map(bar => Number(bar.volume || 0)), 1);
    const yVol = value => volumeBottom - (Number(value || 0) / vMax) * (volumeBottom - volumeTop);
    const hovered = bars[hoverIndex] || bars[bars.length - 1];

    const handleMove = event => {
        if (!bars.length) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
        setHoverIndex(Math.round(ratio * (bars.length - 1)));
    };

    return (
        <svg
            className="native-stock-chart-svg main"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Native candlestick chart with volume and overlays"
            onMouseMove={handleMove}
            onMouseLeave={() => setHoverIndex(null)}
        >
            <ChartGrid
                width={width}
                height={height}
                top={top}
                bottom={bottom}
                left={left}
                right={right}
                yTicks={axisTicks(min, max, 6)}
                yFor={yFor}
                formatY={value => `$${formatNumber(value, 0)}`}
                bars={bars}
                xFor={xFor}
            />

            <g className="native-chart-volume">
                {bars.map((bar, index) => {
                    const x = xFor(index);
                    const up = Number(bar.close) >= Number(bar.open);
                    return (
                        <rect
                            key={`v-${bar.time}`}
                            x={x - candleWidth / 2}
                            y={yVol(bar.volume)}
                            width={candleWidth}
                            height={Math.max(1, volumeBottom - yVol(bar.volume))}
                            className={up ? 'up' : 'down'}
                        />
                    );
                })}
            </g>

            {active.bb && (
                <>
                    <path className="native-chart-band-fill" d={areaPath(overlays.bb_upper, overlays.bb_lower, bars, xFor, yFor)} />
                    <path className="native-chart-overlay bb" d={linePath(overlays.bb_upper, bars, xFor, yFor)} />
                    <path className="native-chart-overlay bb" d={linePath(overlays.bb_lower, bars, xFor, yFor)} />
                </>
            )}
            {active.ma20 && <path className="native-chart-overlay ma20" d={linePath(overlays.ma20, bars, xFor, yFor)} />}
            {active.ma50 && <path className="native-chart-overlay ma50" d={linePath(overlays.ma50, bars, xFor, yFor)} />}
            {active.vwap && <path className="native-chart-overlay vwap" d={linePath(overlays.vwap, bars, xFor, yFor)} />}

            <g className="native-chart-candles">
                {bars.map((bar, index) => {
                    const x = xFor(index);
                    const yOpen = yFor(bar.open);
                    const yClose = yFor(bar.close);
                    const up = Number(bar.close) >= Number(bar.open);
                    return (
                        <g key={bar.time} className={up ? 'up' : 'down'}>
                            <line x1={x} x2={x} y1={yFor(bar.high)} y2={yFor(bar.low)} />
                            <rect
                                x={x - candleWidth / 2}
                                y={Math.min(yOpen, yClose)}
                                width={candleWidth}
                                height={Math.max(2, Math.abs(yOpen - yClose))}
                                rx="1"
                            />
                        </g>
                    );
                })}
            </g>

            {hovered && (
                <g className="native-chart-hover">
                    <line x1={xFor(hoverIndex ?? bars.length - 1)} x2={xFor(hoverIndex ?? bars.length - 1)} y1={top} y2={plotBottom} />
                    <rect x={left + 12} y={top + 10} width="260" height="96" rx="6" />
                    <text x={left + 28} y={top + 34}>{formatDate(hovered.time)}</text>
                    <text x={left + 28} y={top + 58}>O {formatNumber(hovered.open)}  H {formatNumber(hovered.high)}</text>
                    <text x={left + 28} y={top + 80}>L {formatNumber(hovered.low)}  C {formatNumber(hovered.close)}</text>
                    <text x={left + 28} y={top + 102}>Vol {formatNumber(hovered.volume, 0)}</text>
                </g>
            )}
        </svg>
    );
}

function NativeRsiChart({ bars, values, hoverIndex, setHoverIndex }) {
    const { width, rsiHeight: height, left, right, top } = CHART;
    const bottom = 18;
    const plotWidth = width - left - right;
    const xFor = index => left + (bars.length <= 1 ? plotWidth / 2 : (index / (bars.length - 1)) * plotWidth);
    const yFor = makeScale(0, 100, top, height - bottom);

    return (
        <svg
            className="native-stock-chart-svg indicator"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Native RSI chart"
            onMouseMove={event => {
                if (!bars.length) return;
                const rect = event.currentTarget.getBoundingClientRect();
                const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
                setHoverIndex(Math.round(ratio * (bars.length - 1)));
            }}
            onMouseLeave={() => setHoverIndex(null)}
        >
            <ChartGrid
                width={width}
                height={height}
                top={top}
                bottom={bottom}
                left={left}
                right={right}
                yTicks={[30, 50, 70]}
                yFor={yFor}
                formatY={value => formatNumber(value, 0)}
                bars={[]}
                xFor={xFor}
            />
            <rect x={left} y={yFor(70)} width={plotWidth} height={yFor(30) - yFor(70)} className="native-rsi-zone" />
            <line className="native-rsi-guide high" x1={left} x2={width - right} y1={yFor(70)} y2={yFor(70)} />
            <line className="native-rsi-guide low" x1={left} x2={width - right} y1={yFor(30)} y2={yFor(30)} />
            <path className="native-chart-overlay rsi-line" d={linePath(values, bars, xFor, yFor)} />
            {hoverIndex != null && bars[hoverIndex] && (
                <line className="native-chart-hover-line" x1={xFor(hoverIndex)} x2={xFor(hoverIndex)} y1={top} y2={height - bottom} />
            )}
        </svg>
    );
}

function NativeMacdChart({ bars, macd, hoverIndex, setHoverIndex }) {
    const { width, macdHeight: height, left, right, top } = CHART;
    const bottom = 18;
    const plotWidth = width - left - right;
    const xFor = index => left + (bars.length <= 1 ? plotWidth / 2 : (index / (bars.length - 1)) * plotWidth);
    const values = [
        ...(macd.line || []),
        ...(macd.signal || []),
        ...(macd.histogram || []),
        0,
    ].filter(value => value != null && Number.isFinite(Number(value))).map(Number);
    const rawMin = Math.min(...values);
    const rawMax = Math.max(...values);
    const pad = Math.max(1, (rawMax - rawMin) * 0.12);
    const yFor = makeScale(rawMin - pad, rawMax + pad, top, height - bottom);
    const zero = yFor(0);
    const barWidth = clamp((plotWidth / Math.max(bars.length, 1)) * 0.62, 3, 12);

    return (
        <svg
            className="native-stock-chart-svg indicator"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Native MACD chart"
            onMouseMove={event => {
                if (!bars.length) return;
                const rect = event.currentTarget.getBoundingClientRect();
                const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
                setHoverIndex(Math.round(ratio * (bars.length - 1)));
            }}
            onMouseLeave={() => setHoverIndex(null)}
        >
            <ChartGrid
                width={width}
                height={height}
                top={top}
                bottom={bottom}
                left={left}
                right={right}
                yTicks={axisTicks(rawMin - pad, rawMax + pad, 4)}
                yFor={yFor}
                formatY={value => formatNumber(value, 1)}
                bars={[]}
                xFor={xFor}
            />
            <line className="native-macd-zero" x1={left} x2={width - right} y1={zero} y2={zero} />
            <g className="native-macd-histogram">
                {(macd.histogram || []).map((value, index) => {
                    if (value == null) return null;
                    const y = yFor(value);
                    const positive = Number(value) >= 0;
                    return (
                        <rect
                            key={`macd-${bars[index]?.time || index}`}
                            x={xFor(index) - barWidth / 2}
                            y={positive ? y : zero}
                            width={barWidth}
                            height={Math.max(1, Math.abs(zero - y))}
                            className={positive ? 'positive' : 'negative'}
                        />
                    );
                })}
            </g>
            <path className="native-chart-overlay macd-line" d={linePath(macd.line, bars, xFor, yFor)} />
            <path className="native-chart-overlay macd-signal" d={linePath(macd.signal, bars, xFor, yFor)} />
            {hoverIndex != null && bars[hoverIndex] && (
                <line className="native-chart-hover-line" x1={xFor(hoverIndex)} x2={xFor(hoverIndex)} y1={top} y2={height - bottom} />
            )}
        </svg>
    );
}

export default function StockChart({ ticker }) {
    const [range, setRange] = useState('1y');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [active, setActive] = useState({ ma20: true, ma50: true, bb: false, vwap: false });
    const [hoverIndex, setHoverIndex] = useState(null);

    const apiRange = RANGE_MAP[range] || range;

    const load = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const res = await getChart(ticker, apiRange);
            setData(res.data || {});
            if (res.error && !(res.data?.bars?.length)) setError(res.error);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [apiRange, ticker]);

    useEffect(() => {
        const id = window.setTimeout(load, 0);
        return () => window.clearTimeout(id);
    }, [load]);

    const visible = useMemo(() => {
        const rawBars = data?.bars || [];
        const bars = filterBars(rawBars, range);
        const overlays = data?.overlays || {};
        return {
            bars,
            overlays: {
                ma20: sliceAligned(overlays.ma20, rawBars, bars),
                ma50: sliceAligned(overlays.ma50, rawBars, bars),
                bb_upper: sliceAligned(overlays.bb_upper, rawBars, bars),
                bb_lower: sliceAligned(overlays.bb_lower, rawBars, bars),
                vwap: sliceAligned(overlays.vwap, rawBars, bars),
                rsi: sliceAligned(overlays.rsi, rawBars, bars),
                macd: {
                    line: sliceAligned(overlays.macd?.line, rawBars, bars),
                    signal: sliceAligned(overlays.macd?.signal, rawBars, bars),
                    histogram: sliceAligned(overlays.macd?.histogram, rawBars, bars),
                },
            },
        };
    }, [data, range]);

    const stats = useMemo(() => {
        const bars = visible.bars;
        if (!bars.length) return {};
        const first = bars[0].close;
        const last = bars[bars.length - 1].close;
        const changePct = first ? ((last - first) / first) * 100 : null;
        const high = Math.max(...bars.map(bar => Number(bar.high)));
        const low = Math.min(...bars.map(bar => Number(bar.low)));
        const rsi = lastNumber(visible.overlays.rsi);
        const macdHist = lastNumber(visible.overlays.macd.histogram);
        return { last, changePct, high, low, rsi, macdHist };
    }, [visible]);

    const latestHover = hoverIndex == null ? visible.bars.length - 1 : hoverIndex;
    const hoveredRsi = visible.overlays.rsi?.[latestHover];
    const hoveredMacd = visible.overlays.macd?.histogram?.[latestHover];

    return (
        <section className="glass-card custom-stock-chart" id="stock-chart">
            <div className="custom-stock-chart-header">
                <div>
                    <h2 className="stock-section-title">Price & Technicals</h2>
                    <p>{ticker?.toUpperCase()} native technical workspace</p>
                </div>
                <div className="custom-stock-chart-controls">
                    <div className="custom-stock-chart-toggle-group" aria-label="Chart overlays">
                        {OVERLAYS.map(overlay => (
                            <button
                                key={overlay.key}
                                className={active[overlay.key] ? 'active' : ''}
                                onClick={() => setActive(prev => ({ ...prev, [overlay.key]: !prev[overlay.key] }))}
                            >
                                {overlay.label}
                            </button>
                        ))}
                    </div>
                    <div className="custom-stock-chart-toggle-group" aria-label="Chart range">
                        {RANGES.map(value => (
                            <button
                                key={value}
                                className={range === value ? 'active' : ''}
                                onClick={() => setRange(value)}
                            >
                                {value}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {error && <div className="alert alert-error custom-stock-chart-alert">{error}</div>}

            <div className="stock-chart-stat-grid">
                <MiniStat label="Last" value={stats.last == null ? 'N/A' : `$${formatNumber(stats.last)}`} />
                <MiniStat
                    label={`${range} Return`}
                    value={stats.changePct == null ? 'N/A' : formatPercent(stats.changePct, true)}
                    tone={stats.changePct >= 0 ? 'value-positive' : 'value-negative'}
                />
                <MiniStat label="Range High" value={stats.high == null ? 'N/A' : `$${formatNumber(stats.high)}`} />
                <MiniStat label="Range Low" value={stats.low == null ? 'N/A' : `$${formatNumber(stats.low)}`} />
                <MiniStat label="RSI" value={stats.rsi == null ? 'N/A' : formatNumber(stats.rsi, 1)} />
                <MiniStat
                    label="MACD Hist"
                    value={stats.macdHist == null ? 'N/A' : formatNumber(stats.macdHist)}
                    tone={stats.macdHist >= 0 ? 'value-positive' : 'value-negative'}
                />
            </div>

            <div className="custom-stock-chart-frame">
                {loading && (
                    <div className="loading-state custom-stock-chart-loading">
                        <div className="spinner" />
                    </div>
                )}
                {visible.bars.length > 0 && (
                    <>
                        <NativePriceChart
                            bars={visible.bars}
                            overlays={visible.overlays}
                            active={active}
                            hoverIndex={latestHover}
                            setHoverIndex={setHoverIndex}
                        />
                        <div className="custom-stock-chart-pane-label">
                            <span>RSI 14</span>
                            <strong>{hoveredRsi == null ? 'N/A' : formatNumber(hoveredRsi, 1)}</strong>
                        </div>
                        <NativeRsiChart
                            bars={visible.bars}
                            values={visible.overlays.rsi}
                            hoverIndex={latestHover}
                            setHoverIndex={setHoverIndex}
                        />
                        <div className="custom-stock-chart-pane-label">
                            <span>MACD 12 26 9</span>
                            <strong>{hoveredMacd == null ? 'N/A' : formatNumber(hoveredMacd)}</strong>
                        </div>
                        <NativeMacdChart
                            bars={visible.bars}
                            macd={visible.overlays.macd}
                            hoverIndex={latestHover}
                            setHoverIndex={setHoverIndex}
                        />
                    </>
                )}
            </div>

            {!loading && !visible.bars.length && (
                <div className="empty-state custom-stock-chart-empty">
                    <h3>No chart data</h3>
                    <p>Price history is unavailable for this ticker right now.</p>
                </div>
            )}
        </section>
    );
}

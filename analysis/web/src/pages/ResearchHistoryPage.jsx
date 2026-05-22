import { useState, useEffect, useMemo } from 'react';
import { getAllResearchHistory, getResearchReportById, getResearchReportDrift } from '../utils/api';
import ReportView from '../components/ReportView';
import RecommendationPill from '../components/RecommendationPill';

// ── Formatters ────────────────────────────────────────────────────────

function formatDate(isoString) {
    if (!isoString) return 'Unknown';
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

// ── Main Component ────────────────────────────────────────────────────

export default function ResearchHistoryPage() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedReportId, setSelectedReportId] = useState(null);
    const [fullReport, setFullReport] = useState(null);
    const [drift, setDrift] = useState(null);
    const [reportLoading, setReportLoading] = useState(false);

    // Filters
    const [filterRec, setFilterRec] = useState('ALL');
    const [sortBy, setSortBy] = useState('newest');
    const [searchTicker, setSearchTicker] = useState('');

    useEffect(() => {
        async function fetchHistory() {
            try {
                setLoading(true);
                const data = await getAllResearchHistory(100);
                setReports(data.reports || []);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        fetchHistory();
    }, []);

    const handleSelectReport = async (id) => {
        setSelectedReportId(id);
        setReportLoading(true);
        setDrift(null);
        try {
            const [data, driftData] = await Promise.all([
                getResearchReportById(id),
                getResearchReportDrift(id).catch(() => null),
            ]);
            setFullReport(data);
            setDrift(driftData);
        } catch (err) {
            console.error("Failed to fetch full report", err);
            alert("Failed to load full report details.");
            setSelectedReportId(null);
        } finally {
            setReportLoading(false);
        }
    };

    const handleBack = () => {
        setSelectedReportId(null);
        setFullReport(null);
        setDrift(null);
    };

    // Filtered + sorted reports
    const filteredReports = useMemo(() => {
        let list = [...reports];

        // Filter by recommendation
        if (filterRec !== 'ALL') {
            list = list.filter(r => (r.recommendation || '').toUpperCase() === filterRec);
        }

        // Filter by ticker search
        if (searchTicker.trim()) {
            const q = searchTicker.trim().toUpperCase();
            list = list.filter(r => r.ticker.startsWith(q));
        }

        // Sort
        switch (sortBy) {
            case 'oldest':
                list.sort((a, b) => (a.generated_at || '').localeCompare(b.generated_at || ''));
                break;
            case 'cost':
                list.sort((a, b) => (b.total_cost_usd || 0) - (a.total_cost_usd || 0));
                break;
            case 'conviction':
                const convOrder = { HIGH: 3, MEDIUM: 2, LOW: 1 };
                list.sort((a, b) => (convOrder[(b.conviction || '').toUpperCase()] || 0) - (convOrder[(a.conviction || '').toUpperCase()] || 0));
                break;
            default: // newest
                list.sort((a, b) => (b.generated_at || '').localeCompare(a.generated_at || ''));
        }

        return list;
    }, [reports, filterRec, sortBy, searchTicker]);

    if (loading) {
        return <div className="loading-state"><div className="spinner" /></div>;
    }

    if (error) {
        return <div className="alert alert-error">Failed to load history: {error}</div>;
    }

    // ── Detail View ──────────────────────────────────────────────────
    if (selectedReportId) {
        return (
            <div className="fade-in">
                <button className="btn btn-secondary" onClick={handleBack} style={{ marginBottom: 'var(--spacing-lg)' }}>
                    ← Back to History
                </button>

                {reportLoading ? (
                    <div className="loading-state"><div className="spinner" /> Loading report archive...</div>
                ) : fullReport && fullReport.report ? (
                    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
                        <ReportView
                            report={fullReport.report}
                            mode="archived"
                            drift={drift}
                            telemetry={{
                                evidence_tool_count: fullReport.report?.evidence?.results?.length || 0,
                                total_llm_calls: fullReport.total_llm_calls,
                                cost_used_usd: fullReport.total_cost_usd || fullReport.report?.budget_used?.spent_usd || 0,
                                wall_clock_sec: fullReport.wall_clock_sec || fullReport.report?.budget_used?.wall_clock_sec || 0,
                            }}
                        />
                    </div>
                ) : (
                    <div className="alert alert-warning">Report data missing or corrupted.</div>
                )}
            </div>
        );
    }

    // ── List View ────────────────────────────────────────────────────
    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">🕰️ Research History</h1>
                    <p className="page-subtitle">Archive of deep research reports with full telemetry</p>
                </div>
            </div>

            {/* Filter bar */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--spacing-lg)', flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Recommendation filter pills */}
                {['ALL', 'BUY', 'HOLD', 'TRIM', 'AVOID'].map(rec => (
                    <button
                        key={rec}
                        className={`btn ${filterRec === rec ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ fontSize: '0.72rem', padding: '4px 12px' }}
                        onClick={() => setFilterRec(rec)}
                    >
                        {rec}
                    </button>
                ))}

                <div style={{ flex: 1 }} />

                {/* Sort */}
                <select
                    className="input"
                    value={sortBy}
                    onChange={e => setSortBy(e.target.value)}
                    style={{ maxWidth: 160, fontSize: '0.78rem' }}
                >
                    <option value="newest">Newest</option>
                    <option value="oldest">Oldest</option>
                    <option value="cost">Highest Cost</option>
                    <option value="conviction">Highest Conviction</option>
                </select>

                {/* Search */}
                <input
                    className="input"
                    placeholder="Search ticker…"
                    value={searchTicker}
                    onChange={e => setSearchTicker(e.target.value.toUpperCase())}
                    style={{ maxWidth: 140, fontSize: '0.78rem' }}
                />
            </div>

            {filteredReports.length === 0 ? (
                <div className="glass-card">
                    <div className="empty-state">
                        <div className="empty-state-icon">🗄️</div>
                        <h3 style={{ color: 'var(--text-secondary)' }}>No history found</h3>
                        <p style={{ fontSize: '0.825rem' }}>Run a deep research scan to start saving reports.</p>
                    </div>
                </div>
            ) : (
                <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                                <th style={thStyle}>Ticker</th>
                                <th style={thStyle}>Date</th>
                                <th style={thStyle}>Rec</th>
                                <th style={thStyle}>Conv</th>
                                <th style={thStyle}>Target</th>
                                <th style={thStyle}>Calls</th>
                                <th style={thStyle}>Tools</th>
                                <th style={thStyle}>Cost</th>
                                <th style={thStyle}>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredReports.map(report => (
                                <tr key={report.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={tdStyle}>
                                        <span className="ticker-badge">{report.ticker}</span>
                                    </td>
                                    <td style={tdStyle}>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                            {formatDate(report.generated_at)}
                                        </span>
                                    </td>
                                    <td style={tdStyle}>
                                        {report.recommendation ? (
                                            <RecommendationPill recommendation={report.recommendation} conviction={report.conviction} small />
                                        ) : (
                                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                                        )}
                                    </td>
                                    <td style={tdStyle}>
                                        {report.conviction ? (
                                            <span className={`badge badge-${report.conviction === 'HIGH' ? 'green' : report.conviction === 'MEDIUM' ? 'yellow' : 'gray'}`}
                                                  style={{ fontSize: '0.65rem' }}>
                                                {report.conviction}
                                            </span>
                                        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                                    </td>
                                    <td style={tdStyle}>
                                        {report.target_low && report.target_high ? (
                                            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                ${report.target_low} – ${report.target_high}
                                            </span>
                                        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                                    </td>
                                    <td style={tdStyle}>
                                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                            {report.total_llm_calls || '—'}
                                        </span>
                                    </td>
                                    <td style={tdStyle}>
                                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                            {report.tool_call_count || '—'}
                                        </span>
                                    </td>
                                    <td style={tdStyle}>
                                        {report.total_cost_usd > 0 ? (
                                            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                                ${report.total_cost_usd.toFixed(2)}
                                            </span>
                                        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                                    </td>
                                    <td style={tdStyle}>
                                        <button
                                            className="btn btn-secondary"
                                            style={{ padding: '4px 12px', fontSize: '0.72rem' }}
                                            onClick={() => handleSelectReport(report.id)}
                                        >
                                            View Report
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const thStyle = { padding: '10px 12px', fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' };
const tdStyle = { padding: '10px 12px' };

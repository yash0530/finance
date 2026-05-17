import React, { useState, useEffect } from 'react';
import { getAllResearchHistory, getResearchReportById } from '../utils/api';
import FinancialTrendsChart from '../components/FinancialTrendsChart';
import ValuationCard from '../components/ValuationCard';
import RiskCard from '../components/RiskCard';

// ── Sentinel & Formatters ────────────────────────────────────────

function formatDate(isoString) {
    if (!isoString) return 'Unknown';
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

// ── Thesis Card (copied/adapted from DeepResearchPage) ────────
function ThesisCard({ thesis }) {
    if (!thesis) return null;

    return (
        <div className="glass-card" style={{ borderColor: 'rgba(45, 126, 247, 0.25)', marginBottom: 'var(--spacing-lg)' }}>
            {thesis.error && !thesis.summary ? (
                <div className="alert alert-warning">{thesis.summary || 'AI thesis unavailable'}</div>
            ) : (
                <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-md)' }}>
                        <h3 style={{ fontSize: '0.925rem', color: 'var(--text-primary)', margin: 0 }}>🤖 AI Investment Thesis</h3>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <span className={`badge badge-${thesis.recommendation === 'BUY' ? 'green' : thesis.recommendation === 'HOLD' ? 'yellow' : 'red'}`}
                                style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
                                {thesis.recommendation}
                            </span>
                            <span className={`badge ${
                                thesis.conviction === 'HIGH' ? 'badge-green'
                                : thesis.conviction === 'MEDIUM' ? 'badge-yellow'
                                : 'badge-gray'
                            }`} style={{ border: '1px solid', fontSize: '0.7rem' }}>
                                {thesis.conviction} conviction
                            </span>
                        </div>
                    </div>

                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-md)', lineHeight: 1.7 }}>
                        {thesis.summary}
                    </p>

                    {/* Target price range */}
                    {thesis.target_price_range && (
                        <div style={{
                            display: 'flex', gap: 16, padding: '10px 14px', marginBottom: 'var(--spacing-md)',
                            background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', fontSize: '0.78rem'
                        }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>Target Range: </span>
                                <span style={{ fontFamily: 'monospace', color: 'var(--accent-green)' }}>
                                    ${thesis.target_price_range.low} — ${thesis.target_price_range.high}
                                </span>
                            </div>
                            <span style={{ color: 'var(--text-muted)' }}>({thesis.target_price_range.timeframe})</span>
                        </div>
                    )}

                    <div className="grid grid-2" style={{ gap: 'var(--spacing-md)' }}>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-green)', marginBottom: 8 }}>
                                Synthesized Bull Case
                            </div>
                            {(thesis.bull_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-green)', flexShrink: 0 }}>↑</span>{b}
                                </div>
                            ))}
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-red)', marginBottom: 8 }}>
                                Synthesized Bear Case
                            </div>
                            {(thesis.bear_case || []).map((b, i) => (
                                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 8 }}>
                                    <span style={{ color: 'var(--accent-red)', flexShrink: 0 }}>↓</span>{b}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Adversarial Debate Raw Output */}
                    {(thesis._raw_bull_pass || thesis._raw_bear_pass) && (
                        <details style={{ marginTop: 'var(--spacing-md)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 'var(--spacing-sm)' }}>
                            <summary style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', cursor: 'pointer', outline: 'none', padding: '4px 8px' }}>
                                🔍 View AI Adversarial Debate (3-Pass Output)
                            </summary>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', padding: '12px 8px 4px 8px', marginTop: 8, borderTop: '1px solid var(--border-color)' }}>
                                {thesis._raw_bull_pass && (
                                    <div>
                                        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--accent-green)', fontWeight: 700, marginBottom: 8 }}>Pass 1: The Bull</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>{thesis._raw_bull_pass}</div>
                                    </div>
                                )}
                                {thesis._raw_bear_pass && (
                                    <div>
                                        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--accent-red)', fontWeight: 700, marginBottom: 8 }}>Pass 2: The Bear</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>{thesis._raw_bear_pass}</div>
                                    </div>
                                )}
                            </div>
                        </details>
                    )}

                    {thesis.key_catalysts?.length > 0 && (
                        <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-sm) var(--spacing-md)', background: 'rgba(124,58,237,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(124,58,237,0.15)' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--accent-purple)', marginBottom: 6 }}>Key Catalysts</div>
                            {thesis.key_catalysts.map((c, i) => (
                                <div key={i} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', padding: '2px 0' }}>⚡ {c}</div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

// ── Main Component ────────────────────────────────────────────────

export default function ResearchHistoryPage() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedReportId, setSelectedReportId] = useState(null);
    const [fullReport, setFullReport] = useState(null);
    const [reportLoading, setReportLoading] = useState(false);

    useEffect(() => {
        async function fetchHistory() {
            try {
                setLoading(true);
                const data = await getAllResearchHistory(50);
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
        try {
            const data = await getResearchReportById(id);
            setFullReport(data);
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
    };

    if (loading) {
        return <div className="loading-state"><div className="spinner" /></div>;
    }

    if (error) {
        return <div className="alert alert-error">Failed to load history: {error}</div>;
    }

    // Detailed View Mode
    if (selectedReportId) {
        return (
            <div className="fade-in">
                <button className="btn btn-secondary" onClick={handleBack} style={{ marginBottom: 'var(--spacing-lg)' }}>
                    ← Back to History
                </button>
                
                {reportLoading ? (
                    <div className="loading-state"><div className="spinner" /> Loading deep research archive...</div>
                ) : fullReport && fullReport.report ? (
                    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
                        <div className="glass-card" style={{ marginBottom: 'var(--spacing-lg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <span className="ticker-badge" style={{ fontSize: '1.2rem', padding: '6px 16px' }}>
                                        {fullReport.ticker}
                                    </span>
                                    <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Archived Report</h2>
                                </div>
                                <div style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    Generated on {formatDate(fullReport.generated_at)}
                                </div>
                            </div>
                            <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                <div>ID: {fullReport.id.slice(0, 8)}</div>
                                <div>Model: {fullReport.llm_model}</div>
                                <div>LLM Calls: {fullReport.total_llm_calls}</div>
                            </div>
                        </div>

                        {/* Rendering the archived report sections */}
                        {fullReport.report.thesis && <ThesisCard thesis={fullReport.report.thesis} />}
                        
                        {fullReport.report.financial_trends && <FinancialTrendsChart trends={fullReport.report.financial_trends} />}
                        
                        {fullReport.report.valuation && <ValuationCard valuation={fullReport.report.valuation} />}
                        
                        {fullReport.report.risk_management && <RiskCard riskData={fullReport.report.risk_management} />}
                        
                    </div>
                ) : (
                    <div className="alert alert-warning">Report data missing or corrupted.</div>
                )}
            </div>
        );
    }

    // List View Mode
    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">🕰️ Research History</h1>
                    <p className="page-subtitle">Archive of your previously generated deep research reports</p>
                </div>
            </div>

            {reports.length === 0 ? (
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
                                <th style={{ padding: '12px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ticker</th>
                                <th style={{ padding: '12px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Date Generated</th>
                                <th style={{ padding: '12px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Model</th>
                                <th style={{ padding: '12px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>LLM Calls</th>
                                <th style={{ padding: '12px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reports.map(report => (
                                <tr key={report.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ padding: '12px 16px' }}>
                                        <span className="ticker-badge">{report.ticker}</span>
                                    </td>
                                    <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        {formatDate(report.generated_at)}
                                    </td>
                                    <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        {report.llm_model}
                                    </td>
                                    <td style={{ padding: '12px 16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        {report.total_llm_calls}
                                    </td>
                                    <td style={{ padding: '12px 16px' }}>
                                        <button 
                                            className="btn btn-secondary" 
                                            style={{ padding: '4px 12px', fontSize: '0.75rem' }}
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

import { useState } from 'react';
import ResearchHistoryPage from './ResearchHistoryPage';
import MemosTab from '../components/library/MemosTab';

/**
 * Library — saved research reports + Living Memos browser.
 *
 * Reports tab reuses the existing ResearchHistoryPage. Memos tab lists every
 * Living Memo and opens a section-by-section read-only view.
 */
export default function LibraryPage() {
    const [tab, setTab] = useState('reports');

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Library</h1>
                    <p className="page-subtitle">Saved reports + Living Memos</p>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--spacing-lg)' }}>
                <button
                    id="library-tab-reports"
                    className={`btn ${tab === 'reports' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setTab('reports')}
                >Reports</button>
                <button
                    id="library-tab-memos"
                    className={`btn ${tab === 'memos' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setTab('memos')}
                >Memos</button>
            </div>

            {tab === 'reports' ? <ReportsPane /> : <MemosTab />}
        </div>
    );
}

/**
 * ResearchHistoryPage renders its own page-header. We keep it as-is for the
 * Reports tab — the duplicate header is acceptable and avoids invasive edits to
 * a large, well-tested component.
 */
function ReportsPane() {
    return <ResearchHistoryPage embedded />;
}


import { useState } from 'react';
import LLMSettingsPage from './LLMSettingsPage';
import DataTierBadges from '../components/settings/DataTierBadges';
import ThemesEditor from '../components/settings/ThemesEditor';

/**
 * Settings — LLM provider/keys, data-tier badges, and the themes editor.
 */
export default function SettingsPage() {
    const [tab, setTab] = useState('llm');

    return (
        <div className="fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Settings</h1>
                    <p className="page-subtitle">LLM provider · data tiers · themes</p>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--spacing-lg)' }}>
                <button id="settings-tab-llm" className={`btn ${tab === 'llm' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('llm')}>LLM</button>
                <button id="settings-tab-tiers" className={`btn ${tab === 'tiers' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('tiers')}>Data Tiers</button>
                <button id="settings-tab-themes" className={`btn ${tab === 'themes' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab('themes')}>Themes</button>
            </div>

            {tab === 'llm' && <LLMSettingsPage embedded />}
            {tab === 'tiers' && <DataTierBadges />}
            {tab === 'themes' && <ThemesEditor />}
        </div>
    );
}

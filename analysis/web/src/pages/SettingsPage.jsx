import { useState, useEffect } from 'react';
import { getLLMSettings, saveLLMSettings, testLLMConnection } from '../utils/api';
import DataTierBadges from '../components/settings/DataTierBadges';
import ThemesEditor from '../components/settings/ThemesEditor';

const PROVIDERS = [
    {
        id: 'ollama', label: 'Ollama (Local)',
        description: 'Free, runs locally. No API key needed.',
        models: { fast: 'llama3.2', deep: 'llama3.2' },
        fastOptions: ['llama3.2', 'llama3.1', 'mistral', 'phi3', 'gemma2'],
        deepOptions: ['llama3.2', 'llama3.1:70b', 'mistral', 'gemma2:27b'],
        hasBaseUrl: true,
    },
    {
        id: 'gemini', label: 'Google Gemini',
        description: 'Fast + high quality. Free tier available.',
        models: { fast: 'gemini-3.1-flash-lite', deep: 'gemini-3.5-flash' },
        fastOptions: ['gemini-3.1-flash-lite', 'gemini-3.5-flash'],
        deepOptions: ['gemini-3.1-flash-lite', 'gemini-3.5-flash'],
        apiKeyLabel: 'Gemini API Key', apiKeyPlaceholder: 'AIza...',
        signupUrl: 'https://aistudio.google.com/app/apikey',
    },
    {
        id: 'claude', label: 'Anthropic Claude',
        description: 'Best quality for research & analysis.',
        models: { fast: 'claude-3-5-haiku-20241022', deep: 'claude-opus-4-5' },
        fastOptions: ['claude-3-5-haiku-20241022', 'claude-3-haiku-20240307'],
        deepOptions: ['claude-opus-4-5', 'claude-sonnet-4-5', 'claude-3-5-sonnet-20241022'],
        apiKeyLabel: 'Anthropic API Key', apiKeyPlaceholder: 'sk-ant-...',
        signupUrl: 'https://console.anthropic.com/',
    },
];

function LLMSettingsSection() {
    const [settings, setSettings] = useState({ provider: 'ollama', model_fast: 'llama3.2', model_deep: 'llama3.2', base_url: 'http://localhost:11434' });
    const [apiKey, setApiKey]     = useState('');
    const [saving, setSaving]     = useState(false);
    const [testing, setTesting]   = useState(false);
    const [message, setMessage]   = useState(null);
    const [loading, setLoading]   = useState(true);

    useEffect(() => {
        getLLMSettings().then(s => { setSettings(s); setLoading(false); }).catch(() => setLoading(false));
    }, []);

    async function handleSave(e) {
        e.preventDefault();
        setSaving(true); setMessage(null);
        try {
            const res = await saveLLMSettings({ ...settings, api_key: apiKey });
            if (res.success) {
                setMessage({ type: 'success', text: 'Settings saved successfully' });
                setApiKey(''); // clear from UI
            }
        } catch (err) { setMessage({ type: 'error', text: err.message }); }
        finally { setSaving(false); }
    }

    async function handleTest() {
        setTesting(true); setMessage(null);
        try {
            const res = await testLLMConnection();
            if (res.success) setMessage({ type: 'success', text: `Connected. Test score: ${JSON.stringify(res.test_result)}` });
            else setMessage({ type: 'error', text: res.error });
        } catch (err) { setMessage({ type: 'error', text: err.message }); }
        finally { setTesting(false); }
    }

    const provider = PROVIDERS.find(p => p.id === settings.provider) || PROVIDERS[0];

    if (loading) return <div className="loading-state"><div className="spinner" /></div>;

    return (
        <div className="grid grid-2" style={{ gap: 'var(--spacing-xl)', alignItems: 'start' }}>
            {/* Provider selector */}
            <div>
                <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Select Provider</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                    {PROVIDERS.map(p => (
                        <div key={p.id}
                            id={`provider-${p.id}`}
                            onClick={() => setSettings(s => ({ ...s, provider: p.id, model_fast: p.models.fast, model_deep: p.models.deep }))}
                            style={{
                                padding: 'var(--spacing-md)', borderRadius: 'var(--radius-lg)',
                                border: `1px solid ${settings.provider === p.id ? 'var(--accent-blue)' : 'var(--border-color)'}`,
                                background: settings.provider === p.id ? 'rgba(45,126,247,0.08)' : 'var(--bg-card)',
                                cursor: 'pointer', transition: 'all 0.15s ease',
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <span style={{ fontSize: '1.25rem' }}></span>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{p.label}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.description}</div>
                                    </div>
                                </div>
                                {settings.provider === p.id && (
                                    <span style={{ color: 'var(--accent-blue-bright)', fontSize: '0.7rem', fontWeight: 700 }}>SELECTED</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Cost routing info */}
                <div className="glass-card" style={{ marginTop: 'var(--spacing-lg)' }}>
                    <div className="card-title" style={{ marginBottom: 'var(--spacing-sm)' }}>Smart Cost Routing</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        <div><strong>Fast model</strong> — Sentiment scoring, quick summaries</div>
                        <div><strong>Deep model</strong> — Full thesis, EDGAR analysis, comparison</div>
                    </div>
                </div>
            </div>

            {/* Config form */}
            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                <div className="glass-card">
                    <div className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>
                        {provider.label} Configuration
                    </div>

                    {provider.hasBaseUrl && (
                        <div className="input-group" style={{ marginBottom: 'var(--spacing-md)' }}>
                            <label className="input-label">Ollama Base URL</label>
                            <input id="llm-base-url" className="input" type="url"
                                value={settings.base_url || 'http://localhost:11434'}
                                onChange={e => setSettings(s => ({ ...s, base_url: e.target.value }))} />
                        </div>
                    )}

                    {provider.apiKeyLabel && (
                        <div className="input-group" style={{ marginBottom: 'var(--spacing-md)' }}>
                            <label className="input-label">
                                {provider.apiKeyLabel}
                                {provider.signupUrl && (
                                    <a href={provider.signupUrl} target="_blank" rel="noreferrer"
                                        style={{ marginLeft: 8, fontSize: '0.7rem', color: 'var(--accent-blue-bright)' }}>
                                        Get key ↗
                                    </a>
                                )}
                            </label>
                            <input id="llm-api-key" className="input" type="password"
                                placeholder={settings.api_key ? '(saved — enter new to update)' : provider.apiKeyPlaceholder}
                                value={apiKey}
                                onChange={e => setApiKey(e.target.value)} />
                        </div>
                    )}

                    <div className="grid grid-2" style={{ gap: 'var(--spacing-sm)' }}>
                        <div className="input-group">
                            <label className="input-label">Fast Model</label>
                            <select id="llm-model-fast" className="select"
                                value={settings.model_fast}
                                onChange={e => setSettings(s => ({ ...s, model_fast: e.target.value }))}>
                                {provider.fastOptions.map(m => <option key={m} value={m}>{m}</option>)}
                            </select>
                        </div>
                        <div className="input-group">
                            <label className="input-label">Deep Model</label>
                            <select id="llm-model-deep" className="select"
                                value={settings.model_deep}
                                onChange={e => setSettings(s => ({ ...s, model_deep: e.target.value }))}>
                                {provider.deepOptions.map(m => <option key={m} value={m}>{m}</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                {message && (
                    <div className={`alert alert-${message.type}`}>{message.text}</div>
                )}

                <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
                    <button id="btn-save-llm" className="btn btn-primary" type="submit" disabled={saving}>
                        {saving ? <><span className="spinner spinner-sm" /> Saving…</> : 'Save Settings'}
                    </button>
                    <button id="btn-test-llm" className="btn btn-secondary" type="button"
                        onClick={handleTest} disabled={testing}>
                        {testing ? <><span className="spinner spinner-sm" /> Testing…</> : 'Test Connection'}
                    </button>
                </div>
            </form>
        </div>
    );
}

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

            {tab === 'llm' && <LLMSettingsSection />}
            {tab === 'tiers' && <DataTierBadges />}
            {tab === 'themes' && <ThemesEditor />}
        </div>
    );
}

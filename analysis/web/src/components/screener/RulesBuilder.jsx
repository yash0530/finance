import { useState, useEffect } from 'react';
import { getScreenerFields } from '../../utils/api';

const OPS = ['>', '>=', '<', '<=', '=', '!='];
const BOOLEAN_FIELDS = new Set(['ma_50_above_ma_200', 'above_50ma', 'above_200ma']);
const UNIVERSES = ['themes', 'watchlist', 'sp500'];

function RuleRow({ rule, fields, onChange, onRemove }) {
    const isBool = BOOLEAN_FIELDS.has(rule.field);
    return (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
            <select className="select" value={rule.field} onChange={e => onChange({ ...rule, field: e.target.value })} style={{ maxWidth: 220 }}>
                {fields.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
            <select className="select" value={rule.op} onChange={e => onChange({ ...rule, op: e.target.value })} style={{ maxWidth: 70 }}>
                {OPS.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
            {isBool ? (
                <select className="select" value={String(rule.value)} onChange={e => onChange({ ...rule, value: e.target.value === 'true' })} style={{ maxWidth: 90 }}>
                    <option value="true">true</option>
                    <option value="false">false</option>
                </select>
            ) : (
                <input className="input" type="number" step="any" value={rule.value}
                    onChange={e => onChange({ ...rule, value: e.target.value === '' ? '' : Number(e.target.value) })}
                    style={{ maxWidth: 120 }} />
            )}
            <button className="btn btn-secondary" style={{ padding: '2px 10px' }} onClick={onRemove}>×</button>
        </div>
    );
}

export default function RulesBuilder({ spec, onChange, onRun, running }) {
    const [fields, setFields] = useState(['rsi', 'forward_pe', 'yoy_revenue_growth', 'ma_50_above_ma_200']);

    useEffect(() => {
        getScreenerFields().then(res => setFields(res.fields || fields)).catch(() => {});
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const updateRule = (i, rule) => {
        const rules = [...spec.rules];
        rules[i] = rule;
        onChange({ ...spec, rules });
    };
    const removeRule = (i) => onChange({ ...spec, rules: spec.rules.filter((_, idx) => idx !== i) });
    const addRule = () => onChange({ ...spec, rules: [...spec.rules, { field: fields[0], op: '<', value: 30 }] });

    return (
        <div className="glass-card" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 'var(--spacing-md)', flexWrap: 'wrap' }}>
                <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Universe</label>
                <select className="select" value={Array.isArray(spec.universe) ? 'themes' : spec.universe}
                    onChange={e => onChange({ ...spec, universe: e.target.value })} style={{ maxWidth: 160 }}>
                    {UNIVERSES.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
                <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Combine</label>
                <select className="select" value={spec.combine} onChange={e => onChange({ ...spec, combine: e.target.value })} style={{ maxWidth: 90 }}>
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                </select>
            </div>

            {spec.rules.map((r, i) => (
                <RuleRow key={i} rule={r} fields={fields} onChange={(rule) => updateRule(i, rule)} onRemove={() => removeRule(i)} />
            ))}

            <div style={{ display: 'flex', gap: 8, marginTop: 'var(--spacing-sm)' }}>
                <button className="btn btn-secondary" onClick={addRule}>+ Rule</button>
                <button id="screener-run-btn" className="btn btn-primary" onClick={onRun} disabled={running || spec.rules.length === 0}>
                    {running ? <><span className="spinner spinner-sm" /> Running…</> : 'Run screen'}
                </button>
            </div>
        </div>
    );
}

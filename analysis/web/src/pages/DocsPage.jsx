import { useEffect, useState, useMemo, useRef } from 'react';
import { listDocs, getDoc } from '../utils/api';

// ────────────────────────────────────────────────────────────
// Minimal markdown → React renderer.
// Handles: H1/H2/H3, paragraphs, bold/italic/inline-code, fenced
// code blocks, bullet + ordered lists, links, tables, blockquotes,
// horizontal rules. No nested lists. Strips YAML frontmatter.
// ────────────────────────────────────────────────────────────

function stripFrontmatter(md) {
    if (md.startsWith('---\n')) {
        const end = md.indexOf('\n---\n', 4);
        if (end !== -1) return md.slice(end + 5);
    }
    return md;
}

function slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-');
}

function renderInline(text, keyBase) {
    // Process in order: code → bold → italic → links
    const parts = [];
    let remaining = text;
    let idx = 0;

    const pushText = (t) => { if (t) parts.push(t); };

    while (remaining.length > 0) {
        // inline code `...`
        const code = remaining.match(/`([^`]+)`/);
        // bold **...**
        const bold = remaining.match(/\*\*([^*]+)\*\*/);
        // italic *...* (avoid matching bold)
        const italic = remaining.match(/(?<!\*)\*([^*]+)\*(?!\*)/);
        // link [text](url)
        const link = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);

        const candidates = [
            code   && { kind: 'code',   match: code,   index: code.index   },
            bold   && { kind: 'bold',   match: bold,   index: bold.index   },
            italic && { kind: 'italic', match: italic, index: italic.index },
            link   && { kind: 'link',   match: link,   index: link.index   },
        ].filter(Boolean);
        if (candidates.length === 0) {
            pushText(remaining);
            break;
        }
        candidates.sort((a, b) => a.index - b.index);
        const next = candidates[0];

        pushText(remaining.slice(0, next.index));
        if (next.kind === 'code') {
            parts.push(<code key={`${keyBase}-c-${idx++}`} className="md-inline-code">{next.match[1]}</code>);
        } else if (next.kind === 'bold') {
            parts.push(<strong key={`${keyBase}-b-${idx++}`}>{renderInline(next.match[1], `${keyBase}-bi-${idx}`)}</strong>);
        } else if (next.kind === 'italic') {
            parts.push(<em key={`${keyBase}-i-${idx++}`}>{renderInline(next.match[1], `${keyBase}-ii-${idx}`)}</em>);
        } else if (next.kind === 'link') {
            const href = next.match[2];
            const onClickInternal = href.startsWith('#') || (!href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('mailto:'));
            parts.push(
                <a
                    key={`${keyBase}-l-${idx++}`}
                    href={onClickInternal ? '#' : href}
                    data-internal={onClickInternal ? href : undefined}
                    target={onClickInternal ? undefined : '_blank'}
                    rel={onClickInternal ? undefined : 'noreferrer'}
                    className="md-link"
                >
                    {next.match[1]}
                </a>
            );
        }
        remaining = remaining.slice(next.index + next.match[0].length);
    }
    return parts;
}

function renderMarkdown(md) {
    md = stripFrontmatter(md);
    const lines = md.split('\n');
    const blocks = [];
    let i = 0;
    let blockKey = 0;

    while (i < lines.length) {
        const line = lines[i];

        // Fenced code block
        if (line.startsWith('```')) {
            const lang = line.slice(3).trim();
            const codeLines = [];
            i++;
            while (i < lines.length && !lines[i].startsWith('```')) {
                codeLines.push(lines[i]);
                i++;
            }
            i++; // skip closing fence
            blocks.push(
                <pre key={`b-${blockKey++}`} className="md-code-block">
                    <code data-lang={lang}>{codeLines.join('\n')}</code>
                </pre>
            );
            continue;
        }

        // Horizontal rule
        if (/^[-*_]{3,}\s*$/.test(line)) {
            blocks.push(<hr key={`b-${blockKey++}`} className="md-hr" />);
            i++;
            continue;
        }

        // Headings
        const heading = line.match(/^(#{1,6})\s+(.+?)\s*$/);
        if (heading) {
            const level = heading[1].length;
            const text = heading[2];
            const id = slugify(text);
            const Tag = `h${level}`;
            blocks.push(
                <Tag key={`b-${blockKey++}`} id={id} className={`md-h${level}`}>
                    {renderInline(text, `h-${blockKey}`)}
                </Tag>
            );
            i++;
            continue;
        }

        // Blockquote
        if (line.startsWith('> ')) {
            const quoteLines = [];
            while (i < lines.length && lines[i].startsWith('> ')) {
                quoteLines.push(lines[i].slice(2));
                i++;
            }
            blocks.push(
                <blockquote key={`b-${blockKey++}`} className="md-blockquote">
                    {renderInline(quoteLines.join(' '), `bq-${blockKey}`)}
                </blockquote>
            );
            continue;
        }

        // Table
        if (line.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-+/.test(lines[i + 1])) {
            const header = line.split('|').map(c => c.trim()).filter(Boolean);
            i += 2; // skip header and separator
            const rows = [];
            while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
                rows.push(lines[i].split('|').map(c => c.trim()).filter(Boolean));
                i++;
            }
            blocks.push(
                <table key={`b-${blockKey++}`} className="md-table">
                    <thead>
                        <tr>{header.map((h, j) => <th key={j}>{renderInline(h, `th-${j}`)}</th>)}</tr>
                    </thead>
                    <tbody>
                        {rows.map((r, ri) => (
                            <tr key={ri}>{r.map((c, ci) => <td key={ci}>{renderInline(c, `td-${ri}-${ci}`)}</td>)}</tr>
                        ))}
                    </tbody>
                </table>
            );
            continue;
        }

        // Bullet list
        if (/^\s*[-*]\s+/.test(line)) {
            const items = [];
            while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
                const text = lines[i].replace(/^\s*[-*]\s+/, '');
                items.push(text);
                i++;
            }
            blocks.push(
                <ul key={`b-${blockKey++}`} className="md-ul">
                    {items.map((t, j) => <li key={j}>{renderInline(t, `ul-${j}`)}</li>)}
                </ul>
            );
            continue;
        }

        // Ordered list
        if (/^\s*\d+\.\s+/.test(line)) {
            const items = [];
            while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
                const text = lines[i].replace(/^\s*\d+\.\s+/, '');
                items.push(text);
                i++;
            }
            blocks.push(
                <ol key={`b-${blockKey++}`} className="md-ol">
                    {items.map((t, j) => <li key={j}>{renderInline(t, `ol-${j}`)}</li>)}
                </ol>
            );
            continue;
        }

        // Blank line
        if (line.trim() === '') {
            i++;
            continue;
        }

        // Paragraph — gather consecutive non-blank, non-special lines
        const paraLines = [];
        while (
            i < lines.length &&
            lines[i].trim() !== '' &&
            !lines[i].startsWith('#') &&
            !lines[i].startsWith('```') &&
            !lines[i].startsWith('> ') &&
            !/^\s*[-*]\s+/.test(lines[i]) &&
            !/^\s*\d+\.\s+/.test(lines[i]) &&
            !/^[-*_]{3,}\s*$/.test(lines[i])
        ) {
            paraLines.push(lines[i]);
            i++;
        }
        if (paraLines.length > 0) {
            blocks.push(
                <p key={`b-${blockKey++}`} className="md-p">
                    {renderInline(paraLines.join(' '), `p-${blockKey}`)}
                </p>
            );
        }
    }
    return blocks;
}

// ────────────────────────────────────────────────────────────
// Page component
// ────────────────────────────────────────────────────────────

export default function DocsPage() {
    const [index, setIndex] = useState([]);
    const [activeSlug, setActiveSlug] = useState(null);
    const [doc, setDoc] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const contentRef = useRef(null);

    useEffect(() => {
        listDocs()
            .then(res => {
                setIndex(res.docs || []);
                if ((res.docs || []).length > 0 && !activeSlug) {
                    setActiveSlug(res.docs[0].slug);
                }
            })
            .catch(e => setError(`Failed to load doc index: ${e.message}`));
    }, []);

    useEffect(() => {
        if (!activeSlug) return;
        setLoading(true);
        setError(null);
        getDoc(activeSlug)
            .then(d => { setDoc(d); setLoading(false); })
            .catch(e => { setError(`Failed to load doc: ${e.message}`); setLoading(false); });
    }, [activeSlug]);

    // Handle internal markdown link clicks (slug or anchor)
    useEffect(() => {
        const el = contentRef.current;
        if (!el) return;
        function handler(e) {
            const a = e.target.closest('a[data-internal]');
            if (!a) return;
            e.preventDefault();
            const target = a.getAttribute('data-internal');
            if (target.startsWith('#')) {
                const anchor = target.slice(1);
                const node = el.querySelector(`#${CSS.escape(anchor)}`);
                if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }
            // Treat as slug
            const slug = target.replace(/\.md$/, '');
            if (index.some(d => d.slug === slug)) {
                setActiveSlug(slug);
            }
        }
        el.addEventListener('click', handler);
        return () => el.removeEventListener('click', handler);
    }, [doc, index]);

    const grouped = useMemo(() => {
        const out = {};
        for (const d of index) {
            (out[d.category] = out[d.category] || []).push(d);
        }
        return out;
    }, [index]);

    return (
        <div className="docs-shell" style={{ display: 'grid', gridTemplateColumns: '220px 1fr 200px', gap: 'var(--spacing-lg)' }}>
            {/* Left: doc index */}
            <aside className="glass-card" style={{ position: 'sticky', top: 0, alignSelf: 'start', maxHeight: 'calc(100vh - 40px)', overflowY: 'auto' }}>
                <h1 style={{ fontSize: '1rem', marginBottom: 'var(--spacing-md)' }}>Docs</h1>
                {Object.entries(grouped).map(([cat, docs]) => (
                    <div key={cat} style={{ marginBottom: 'var(--spacing-md)' }}>
                        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4, letterSpacing: '0.05em' }}>
                            {cat}
                        </div>
                        {docs.map(d => (
                            <button
                                key={d.slug}
                                onClick={() => setActiveSlug(d.slug)}
                                className="docs-nav-item"
                                style={{
                                    display: 'block', width: '100%', textAlign: 'left',
                                    padding: '6px 8px', marginBottom: 2,
                                    background: d.slug === activeSlug ? 'var(--bg-elevated)' : 'transparent',
                                    border: 'none',
                                    color: d.slug === activeSlug ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem',
                                    borderRadius: 4,
                                }}
                            >
                                {d.title}
                            </button>
                        ))}
                    </div>
                ))}
            </aside>

            {/* Center: rendered markdown */}
            <main>
                {error && <div className="glass-card" style={{ color: 'var(--accent-red)' }}>{error}</div>}
                {loading && <div className="loading-state" style={{ minHeight: 200 }}><div className="spinner" /></div>}
                {!loading && doc && (
                    <article ref={contentRef} className="docs-content markdown-body" style={{ padding: 'var(--spacing-md)' }}>
                        {renderMarkdown(doc.body)}
                    </article>
                )}
                {!loading && !doc && !error && (
                    <div className="glass-card" style={{ color: 'var(--text-muted)' }}>No doc selected.</div>
                )}
            </main>

            {/* Right: TOC */}
            <aside style={{ position: 'sticky', top: 0, alignSelf: 'start', maxHeight: 'calc(100vh - 40px)', overflowY: 'auto' }}>
                {doc && doc.toc && doc.toc.length > 0 && (
                    <div className="glass-card">
                        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, letterSpacing: '0.05em' }}>
                            On this page
                        </div>
                        {doc.toc.map((h, i) => (
                            <a
                                key={i}
                                href={`#${h.anchor}`}
                                onClick={(e) => {
                                    e.preventDefault();
                                    const node = contentRef.current?.querySelector(`#${CSS.escape(h.anchor)}`);
                                    if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                }}
                                style={{
                                    display: 'block',
                                    fontSize: '0.78rem',
                                    color: 'var(--text-secondary)',
                                    paddingLeft: (h.level - 2) * 12,
                                    paddingTop: 3,
                                    paddingBottom: 3,
                                    textDecoration: 'none',
                                }}
                            >
                                {h.text}
                            </a>
                        ))}
                    </div>
                )}
            </aside>
        </div>
    );
}

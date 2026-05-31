import { useState, useEffect, useCallback } from 'react';

function parseHash() {
    const raw = window.location.hash.replace(/^#/, '');
    const [path, query] = raw.split('?');
    const params = {};
    if (query) {
        for (const [k, v] of new URLSearchParams(query)) params[k] = v;
    }
    return { page: path || 'discover', params };
}

export function buildHash(page, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return `#${page}${qs ? '?' + qs : ''}`;
}

export function navigate(page, params = {}) {
    window.location.hash = buildHash(page, params);
}

export function useHashRoute() {
    const [route, setRoute] = useState(parseHash);

    useEffect(() => {
        const onChange = () => setRoute(parseHash());
        window.addEventListener('hashchange', onChange);
        return () => window.removeEventListener('hashchange', onChange);
    }, []);

    const go = useCallback((page, params = {}) => navigate(page, params), []);

    return { ...route, go };
}

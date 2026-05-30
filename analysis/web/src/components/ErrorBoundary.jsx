import { Component } from 'react';

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an exception:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            const fallback = this.props.fallback;
            if (fallback) return fallback;

            return (
                <div className="glass-card" style={{
                    cursor: 'default', borderLeft: '4px solid var(--accent-red, #DB4437)',
                    padding: 'var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: 6
                }}>
                    <strong style={{ fontSize: '0.82rem', color: 'var(--accent-red, #DB4437)' }}>
                        Component Load Failure
                    </strong>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                        This section failed to render due to an unexpected error.
                    </div>
                    {this.state.error && (
                        <pre style={{
                            margin: '4px 0 0 0', padding: 6, fontSize: '0.64rem', fontFamily: 'var(--font-mono, monospace)',
                            background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 4,
                            overflowX: 'auto', color: 'rgba(255,255,255,0.6)'
                        }}>
                            {this.state.error.toString()}
                        </pre>
                    )}
                </div>
            );
        }

        return this.props.children;
    }
}

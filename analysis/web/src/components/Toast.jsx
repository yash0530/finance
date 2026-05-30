import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ToastContext = createContext(null);

export function useToast() {
    return useContext(ToastContext);
}

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const showToast = useCallback((message, type = 'info') => {
        const id = Math.random().toString(36).substring(2, 9);
        setToasts(prev => [...prev, { id, message, type }]);
        // Auto-remove after 4.5 seconds
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 4500);
    }, []);

    // Decoupled global error listener
    useEffect(() => {
        const handleGlobalError = (e) => {
            if (e.detail) {
                showToast(e.detail, 'error');
            }
        };
        window.addEventListener('toast-error', handleGlobalError);
        return () => window.removeEventListener('toast-error', handleGlobalError);
    }, [showToast]);

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            {/* Toast Container */}
            <div style={{
                position: 'fixed', bottom: 20, right: 20, zIndex: 9999,
                display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320, pointerEvents: 'none'
            }}>
                {toasts.map(t => (
                    <div
                        key={t.id}
                        className={`fade-in`}
                        style={{
                            pointerEvents: 'auto', padding: '10px 14px', borderRadius: 'var(--radius-md, 6px)',
                            background: t.type === 'error' ? 'rgba(219,68,55,0.95)' :
                                        t.type === 'success' ? 'rgba(15,157,88,0.95)' : 'rgba(45,126,247,0.95)',
                            color: '#fff', fontSize: '0.78rem', fontWeight: 500,
                            boxShadow: '0 4px 12px rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
                            animation: 'slide-in 0.2s ease forwards'
                        }}
                    >
                        <span>{t.message}</span>
                        <button
                            onClick={() => setToasts(prev => prev.filter(item => item.id !== t.id))}
                            style={{
                                background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer',
                                fontSize: '0.9rem', opacity: 0.7, padding: 0, display: 'flex', alignItems: 'center'
                            }}
                        >&times;</button>
                    </div>
                ))}
            </div>
            {/* Slide-in Keyframe style injector */}
            <style dangerouslySetInnerHTML={{ __html: `
                @keyframes slide-in {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
            `}} />
        </ToastContext.Provider>
    );
}

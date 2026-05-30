export default function RefreshButton({ onClick, loading, label = 'Refresh', id }) {
    return (
        <button
            id={id}
            className="btn btn-secondary"
            style={{ fontSize: '0.72rem', padding: '2px 10px' }}
            onClick={onClick}
            disabled={loading}
        >
            {loading ? <span className="spinner spinner-sm" /> : label}
        </button>
    );
}

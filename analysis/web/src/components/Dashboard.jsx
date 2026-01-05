import { getSectorColor, formatCurrency } from '../utils/api';
import './Dashboard.css';

function Dashboard({ sectors, onSectorSelect }) {
    if (!sectors || sectors.length === 0) {
        return <div className="dashboard-empty">No sector data available</div>;
    }

    return (
        <section className="dashboard">
            <h2 className="section-title">Sectors Overview</h2>
            <p className="section-subtitle">Click a sector to explore companies</p>

            <div className="sector-grid">
                {sectors.map((sector, index) => (
                    <div
                        key={sector.name}
                        className="sector-card glass-card fade-in"
                        style={{
                            animationDelay: `${index * 0.05}s`,
                            borderLeftColor: getSectorColor(sector.name)
                        }}
                        onClick={() => onSectorSelect(sector.name)}
                    >
                        <div className="sector-header">
                            <h3 className="sector-name">{sector.name}</h3>
                            <span
                                className="sector-count"
                                style={{ background: getSectorColor(sector.name) }}
                            >
                                {sector.count}
                            </span>
                        </div>

                        <div className="sector-stats">
                            <div className="stat-item">
                                <span className="stat-label">Avg Forward P/E</span>
                                <span className="stat-value">
                                    {sector.avg_forward_pe?.toFixed(1) || 'N/A'}
                                </span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Market Cap</span>
                                <span className="stat-value">
                                    {sector.total_market_cap_fmt || 'N/A'}
                                </span>
                            </div>
                        </div>

                        <div className="sector-bar">
                            <div
                                className="sector-bar-fill"
                                style={{
                                    width: `${Math.min((sector.avg_forward_pe || 0) / 40 * 100, 100)}%`,
                                    background: getSectorColor(sector.name)
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

export default Dashboard;

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './GlobalMetaDashboard.css';

interface Brawler {
    brawler_id: number;
    brawler_name: string;
    win_rate: number;
    pick_rate: number;
    games: number;
    data_quality: string;
}

interface TrendBrawler {
    brawler_id: number;
    brawler_name: string;
    win_rate: number;
    pick_rate: number;
    trend_strength: number;
    popularity_rank: number;
}

interface Insight {
    id: number;
    timestamp: string;
    type: string;
    title: string;
    content: string;
    confidence: number;
    impact: string;
}

interface GlobalMetaData {
    timestamp: string;
    total_battles: number;
    total_players: number;
    data: {
        top_brawlers: Brawler[];
        mode_breakdown: any;
    };
    ai_insights: string;
    ai_generated_at: string | null;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const GlobalMetaDashboard: React.FC = () => {
    const [globalMeta, setGlobalMeta] = useState<GlobalMetaData | null>(null);
    const [trends, setTrends] = useState<{ rising: TrendBrawler[]; falling: TrendBrawler[] } | null>(null);
    const [insights, setInsights] = useState<Insight[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'insights'>('overview');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchAllData();

        // Refresh every 1 minute for near real-time updates
        const interval = setInterval(fetchAllData, 1 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const fetchAllData = async () => {
        try {
            setLoading(true);
            setError(null);

            const [metaRes, trendsRes, insightsRes] = await Promise.allSettled([
                fetch(`${API_BASE_URL}/api/meta/global`).then(r => r.ok ? r.json() : Promise.reject(r)),
                fetch(`${API_BASE_URL}/api/meta/trends`).then(r => r.ok ? r.json() : Promise.reject(r)),
                fetch(`${API_BASE_URL}/api/meta/insights?limit=10`).then(r => r.ok ? r.json() : Promise.reject(r))
            ]);

            if (metaRes.status === 'fulfilled') {
                setGlobalMeta(metaRes.value);
            }

            if (trendsRes.status === 'fulfilled') {
                setTrends({
                    rising: trendsRes.value.rising_brawlers,
                    falling: trendsRes.value.falling_brawlers
                });
            }

            if (insightsRes.status === 'fulfilled') {
                setInsights(insightsRes.value.insights);
            }

            setLoading(false);
        } catch (err: any) {
            console.error('Error fetching dashboard data:', err);
            setError(err.detail || 'Failed to load meta data');
            setLoading(false);
        }
    };

    const formatNumber = (num: number): string => {
        return new Intl.NumberFormat('fr-FR').format(num);
    };

    const getWinRateColor = (winRate: number): string => {
        if (winRate >= 55) return 'var(--win-rate-high)';
        if (winRate >= 50) return 'var(--win-rate-medium)';
        return 'var(--win-rate-low)';
    };

    const getTierFromWinRate = (winRate: number): string => {
        if (winRate >= 55) return 'S';
        if (winRate >= 52) return 'A';
        if (winRate >= 50) return 'B';
        if (winRate >= 48) return 'C';
        return 'D';
    };

    const getImpactBadgeClass = (impact: string): string => {
        return `impact-badge impact-${impact.toLowerCase()}`;
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Chargement des données de méta globale...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-container">
                <div className="error-state">
                    <div className="error-icon">⚠️</div>
                    <h3>Données non disponibles</h3>
                    <p>{error}</p>
                    <p className="error-hint">
                        Les données globales seront disponibles après la première collecte (toutes les heures).
                    </p>
                    <button className="retry-button" onClick={fetchAllData}>
                        Réessayer
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            {/* Header */}
            <header className="dashboard-header">
                <div className="header-content">
                    <div className="header-title">
                        <h1>🌍 Méta Globale</h1>
                        <p className="subtitle">Intelligence en temps réel propulsée par l'IA</p>
                    </div>
                    {globalMeta && (
                        <div className="header-stats">
                            <div className="stat-pill">
                                <span className="stat-label">Battles Analysées</span>
                                <span className="stat-value">{formatNumber(globalMeta.total_battles)}</span>
                            </div>
                            <div className="stat-pill">
                                <span className="stat-label">Joueurs</span>
                                <span className="stat-value">{formatNumber(globalMeta.total_players)}</span>
                            </div>
                            <div className="stat-pill">
                                <span className="stat-label">Dernière MAJ</span>
                                <span className="stat-value">
                                    {new Date(globalMeta.timestamp).toLocaleTimeString('fr-FR', {
                                        hour: '2-digit',
                                        minute: '2-digit'
                                    })}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </header>

            {/* Tab Navigation */}
            <nav className="tab-navigation">
                <button
                    className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('overview')}
                >
                    <span className="tab-icon">📊</span>
                    Vue d'ensemble
                </button>
                <button
                    className={`tab-button ${activeTab === 'trends' ? 'active' : ''}`}
                    onClick={() => setActiveTab('trends')}
                >
                    <span className="tab-icon">📈</span>
                    Tendances
                </button>
                <button
                    className={`tab-button ${activeTab === 'insights' ? 'active' : ''}`}
                    onClick={() => setActiveTab('insights')}
                >
                    <span className="tab-icon">🤖</span>
                    Insights IA
                </button>
            </nav>

            {/* Tab Content */}
            <main className="dashboard-content">
                {/* Overview Tab */}
                {activeTab === 'overview' && globalMeta && (
                    <div className="tab-panel fade-in">
                        {/* Tier List */}
                        <section className="section">
                            <h2 className="section-title">
                                <span className="title-icon">👑</span>
                                Tier List Globale
                            </h2>
                            <div className="tier-grid">
                                {['S', 'A', 'B', 'C', 'D'].map(tier => {
                                    const brawlersInTier = globalMeta.data.top_brawlers.filter(
                                        b => getTierFromWinRate(b.win_rate) === tier
                                    );

                                    if (brawlersInTier.length === 0) return null;

                                    return (
                                        <div key={tier} className={`tier-row tier-${tier.toLowerCase()}`}>
                                            <div className="tier-label">
                                                <span className="tier-badge">{tier}</span>
                                            </div>
                                            <div className="tier-brawlers">
                                                {brawlersInTier.map(brawler => (
                                                    <div key={brawler.brawler_id} className="brawler-card">
                                                        <div className="brawler-header">
                                                            <span className="brawler-name">{brawler.brawler_name}</span>
                                                            <span
                                                                className="win-rate-badge"
                                                                style={{ backgroundColor: getWinRateColor(brawler.win_rate) }}
                                                            >
                                                                {brawler.win_rate.toFixed(1)}%
                                                            </span>
                                                        </div>
                                                        <div className="brawler-stats">
                                                            <div className="stat-item">
                                                                <span className="stat-icon">🎯</span>
                                                                <span className="stat-text">{brawler.pick_rate.toFixed(1)}% pick</span>
                                                            </div>
                                                            <div className="stat-item">
                                                                <span className="stat-icon">🎮</span>
                                                                <span className="stat-text">{formatNumber(brawler.games)} games</span>
                                                            </div>
                                                        </div>
                                                        <div className="quality-indicator">
                                                            <div
                                                                className={`quality-dot quality-${brawler.data_quality}`}
                                                                title={`Qualité: ${brawler.data_quality}`}
                                                            />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </section>

                        {/* AI Insights Section */}
                        {globalMeta.ai_insights && (
                            <section className="section">
                                <h2 className="section-title">
                                    <span className="title-icon">🤖</span>
                                    Analyse IA
                                    {globalMeta.ai_generated_at && (
                                        <span className="ai-timestamp">
                                            Généré à {new Date(globalMeta.ai_generated_at).toLocaleTimeString('fr-FR')}
                                        </span>
                                    )}
                                </h2>
                                <div className="ai-insights-box">
                                    <div className="markdown-content">
                                        <ReactMarkdown>
                                            {globalMeta.ai_insights}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </section>
                        )}
                    </div>
                )}

                {/* Trends Tab */}
                {activeTab === 'trends' && trends && (
                    <div className="tab-panel fade-in">
                        <div className="trends-grid">
                            {/* Rising Brawlers */}
                            <section className="section">
                                <h2 className="section-title trending-up">
                                    <span className="title-icon">📈</span>
                                    En Montée
                                </h2>
                                <div className="trends-list">
                                    {trends.rising.map((brawler, index) => (
                                        <div key={brawler.brawler_id} className="trend-card rising">
                                            <div className="trend-rank">#{index + 1}</div>
                                            <div className="trend-info">
                                                <div className="trend-header">
                                                    <span className="trend-name">{brawler.brawler_name}</span>
                                                    <div className="trend-strength">
                                                        <div
                                                            className="strength-bar"
                                                            style={{ width: `${brawler.trend_strength * 100}%` }}
                                                        />
                                                        <span className="strength-label">
                                                            +{(brawler.trend_strength * 100).toFixed(0)}%
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="trend-stats">
                                                    <span className="trend-stat">
                                                        WR: <strong>{brawler.win_rate.toFixed(1)}%</strong>
                                                    </span>
                                                    <span className="trend-stat">
                                                        Pick: <strong>{brawler.pick_rate.toFixed(1)}%</strong>
                                                    </span>
                                                    <span className="trend-stat">
                                                        Rank #{brawler.popularity_rank}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Falling Brawlers */}
                            <section className="section">
                                <h2 className="section-title trending-down">
                                    <span className="title-icon">📉</span>
                                    En Descente
                                </h2>
                                <div className="trends-list">
                                    {trends.falling.map((brawler, index) => (
                                        <div key={brawler.brawler_id} className="trend-card falling">
                                            <div className="trend-rank">#{index + 1}</div>
                                            <div className="trend-info">
                                                <div className="trend-header">
                                                    <span className="trend-name">{brawler.brawler_name}</span>
                                                    <div className="trend-strength falling">
                                                        <div
                                                            className="strength-bar"
                                                            style={{ width: `${brawler.trend_strength * 100}%` }}
                                                        />
                                                        <span className="strength-label">
                                                            -{(brawler.trend_strength * 100).toFixed(0)}%
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="trend-stats">
                                                    <span className="trend-stat">
                                                        WR: <strong>{brawler.win_rate.toFixed(1)}%</strong>
                                                    </span>
                                                    <span className="trend-stat">
                                                        Pick: <strong>{brawler.pick_rate.toFixed(1)}%</strong>
                                                    </span>
                                                    <span className="trend-stat">
                                                        Rank #{brawler.popularity_rank}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        </div>
                    </div>
                )}

                {/* Insights Tab */}
                {activeTab === 'insights' && (
                    <div className="tab-panel fade-in">
                        <section className="section">
                            <h2 className="section-title">
                                <span className="title-icon">💡</span>
                                Insights Générés par l'IA
                            </h2>
                            <div className="insights-grid">
                                {insights.length === 0 ? (
                                    <div className="no-insights">
                                        <p>Aucun insight disponible pour le moment.</p>
                                        <p className="hint">Les insights seront générés automatiquement lors des prochaines analyses.</p>
                                    </div>
                                ) : (
                                    insights.map(insight => (
                                        <div key={insight.id} className="insight-card">
                                            <div className="insight-header">
                                                <span className={getImpactBadgeClass(insight.impact)}>
                                                    {insight.impact.toUpperCase()}
                                                </span>
                                                <span className="insight-type">{insight.type.replace('_', ' ')}</span>
                                            </div>
                                            <h3 className="insight-title">{insight.title}</h3>
                                            <p className="insight-content">{insight.content}</p>
                                            <div className="insight-footer">
                                                <div className="confidence-meter">
                                                    <span className="confidence-label">Confiance</span>
                                                    <div className="confidence-bar-container">
                                                        <div
                                                            className="confidence-bar"
                                                            style={{ width: `${insight.confidence * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="confidence-value">
                                                        {(insight.confidence * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                                <span className="insight-time">
                                                    {new Date(insight.timestamp).toLocaleDateString('fr-FR')}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </section>
                    </div>
                )}
            </main>
        </div>
    );
};

export default GlobalMetaDashboard;

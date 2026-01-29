/**
 * Club Stats Component
 * Displays overall club statistics
 */

import React from 'react';
import { ClubStats as ClubStatsType } from '../services/clubApi';
import { useApi } from '../hooks/useApi';
import { clubService } from '../services/clubApi';
import './ClubStats.css';

interface ClubStatsProps {
    clubTag: string;
}

const ClubStats: React.FC<ClubStatsProps> = ({ clubTag }) => {
    const { data, loading, error } = useApi<ClubStatsType>(
        () => clubService.getClubStats(clubTag),
        [clubTag]
    );

    if (loading) {
        return (
            <div className="club-stats loading">
                <div className="spinner"></div>
                <p>Loading club stats...</p>
            </div>
        );
    }

    if (error || !data) {
        const errorMessage = error instanceof Error ? error.message : (error || 'Failed to load club stats');
        return (
            <div className="club-stats error">
                <p>❌ {errorMessage}</p>
            </div>
        );
    }

    const getTypeLabel = (type: string) => {
        switch (type) {
            case 'open': return '🌐 Open';
            case 'inviteOnly': return '📨 Invite Only';
            case 'closed': return '🔒 Closed';
            default: return type;
        }
    };

    return (
        <div className="club-stats">
            <div className="club-header">
                <div className="club-title">
                    <h2>{data.name}</h2>
                    <span className="club-tag">{data.tag}</span>
                </div>
                <span className="club-type">{getTypeLabel(data.type)}</span>
            </div>

            {data.description && (
                <p className="club-description">{data.description}</p>
            )}

            <div className="stats-grid">
                <div className="stat-card primary">
                    <span className="stat-icon">🏆</span>
                    <div className="stat-content">
                        <span className="stat-value">{data.total_trophies.toLocaleString()}</span>
                        <span className="stat-label">Total Trophies</span>
                    </div>
                </div>

                <div className="stat-card">
                    <span className="stat-icon">👥</span>
                    <div className="stat-content">
                        <span className="stat-value">{data.member_count}/30</span>
                        <span className="stat-label">Members</span>
                    </div>
                </div>

                <div className="stat-card">
                    <span className="stat-icon">📊</span>
                    <div className="stat-content">
                        <span className="stat-value">{Math.round(data.average_trophies).toLocaleString()}</span>
                        <span className="stat-label">Average Trophies</span>
                    </div>
                </div>

                <div className="stat-card">
                    <span className="stat-icon">🎯</span>
                    <div className="stat-content">
                        <span className="stat-value">{data.required_trophies.toLocaleString()}</span>
                        <span className="stat-label">Required Trophies</span>
                    </div>
                </div>
            </div>

            {data.top_player && (
                <div className="top-player">
                    <h3>👑 Top Player</h3>
                    <div className="player-info">
                        <div>
                            <span className="player-name">{data.top_player.name}</span>
                            <span className="player-tag">{data.top_player.tag}</span>
                        </div>
                        <span className="player-trophies">
                            {data.top_player.trophies.toLocaleString()} 🏆
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ClubStats;

/**
 * Club Member List Component
 * Displays ranked list of club members
 */

import React, { useState } from 'react';
import { ClubMember } from '../services/clubApi';
import { useApi } from '../hooks/useApi';
import { clubService } from '../services/clubApi';
import './ClubMemberList.css';

interface ClubMemberListProps {
    clubTag: string;
}

const ClubMemberList: React.FC<ClubMemberListProps> = ({ clubTag }) => {
    const { data, loading, error } = useApi<{ members: ClubMember[]; total: number }>(
        () => clubService.getClubMembers(clubTag),
        [clubTag]
    );

    const [sortBy, setSortBy] = useState<'rank' | 'trophies'>('rank');

    if (loading) {
        return (
            <div className="club-member-list loading">
                <div className="spinner"></div>
                <p>Loading members...</p>
            </div>
        );
    }

    if (error || !data) {
        const errorMessage = error instanceof Error ? error.message : (error || 'Failed to load members');
        return (
            <div className="club-member-list error">
                <p>❌ {errorMessage}</p>
            </div>
        );
    }

    const getRoleIcon = (role: string): string => {
        switch (role) {
            case 'president': return '👑';
            case 'vicePresident': return '⭐';
            case 'senior': return '🌟';
            default: return '👤';
        }
    };

    const getRoleLabel = (role: string): string => {
        switch (role) {
            case 'president': return 'President';
            case 'vicePresident': return 'Vice President';
            case 'senior': return 'Senior';
            default: return 'Member';
        }
    };

    const getRankMedal = (rank: number): string => {
        if (rank === 1) return '🥇';
        if (rank === 2) return '🥈';
        if (rank === 3) return '🥉';
        return `#${rank}`;
    };

    return (
        <div className="club-member-list">
            <div className="list-header">
                <h3>👥 Members ({data.total})</h3>
                <div className="sort-controls">
                    <button
                        className={sortBy === 'rank' ? 'active' : ''}
                        onClick={() => setSortBy('rank')}
                    >
                        By Rank
                    </button>
                    <button
                        className={sortBy === 'trophies' ? 'active' : ''}
                        onClick={() => setSortBy('trophies')}
                    >
                        By Trophies
                    </button>
                </div>
            </div>

            <div className="members-container">
                {data.members.map((member) => (
                    <div key={member.tag} className={`member-card rank-${member.rank}`}>
                        <div className="member-rank">
                            <span className="rank-badge">{getRankMedal(member.rank)}</span>
                        </div>

                        <div className="member-info">
                            <div className="member-name-row">
                                <span className="role-icon">{getRoleIcon(member.role)}</span>
                                <div className="member-details">
                                    <span className="member-name">{member.name}</span>
                                    <span className="member-role">{getRoleLabel(member.role)}</span>
                                </div>
                            </div>
                            <span className="member-tag">{member.tag}</span>
                        </div>

                        <div className="member-trophies">
                            <span className="trophy-count">{member.trophies.toLocaleString()}</span>
                            <span className="trophy-icon">🏆</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ClubMemberList;

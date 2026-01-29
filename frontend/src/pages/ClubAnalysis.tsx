/**
 * Club Analysis Page
 * Displays club statistics and member rankings
 */

import React, { useState } from 'react';
import ClubStats from '../components/ClubStats';
import ClubMemberList from '../components/ClubMemberList';
import { useToast } from '../context/ToastContext';
import './ClubAnalysis.css';

const ClubAnalysis: React.FC = () => {
    const [clubTag, setClubTag] = useState('');
    const [searchTag, setSearchTag] = useState('');
    const { showError } = useToast();

    const handleSearch = () => {
        const tag = clubTag.trim();
        if (!tag) {
            showError('Please enter a club tag');
            return;
        }
        setSearchTag(tag);
    };

    return (
        <div className="club-analysis-page">
            <div className="page-header">
                <h1>🏆 Club Analysis</h1>
                <p>Analyze club performance and member rankings</p>
            </div>

            <div className="search-section">
                <div className="search-box">
                    <input
                        type="text"
                        className="club-tag-input"
                        placeholder="Enter club tag (e.g., 2PP or #2PP)"
                        value={clubTag}
                        onChange={(e) => setClubTag(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                    <button className="search-button" onClick={handleSearch}>
                        Search Club
                    </button>
                </div>
                <p className="search-hint">
                    💡 You can find your club tag in-game in the club info screen
                </p>
            </div>

            {searchTag && (
                <div className="club-content">
                    <ClubStats clubTag={searchTag} />
                    <ClubMemberList clubTag={searchTag} />
                </div>
            )}

            {!searchTag && (
                <div className="empty-state">
                    <span className="empty-icon">🔍</span>
                    <h3>Search for a Club</h3>
                    <p>Enter a club tag above to view statistics and member rankings</p>
                </div>
            )}
        </div>
    );
};

export default ClubAnalysis;

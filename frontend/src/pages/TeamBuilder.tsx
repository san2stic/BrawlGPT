/**
 * Team Builder Page
 * Standalone page for team composition building
 */

import React from 'react';
import TeamCompositionBuilder from '../components/TeamCompositionBuilder';
import './TeamBuilder.css';

const TeamBuilder: React.FC = () => {
    return (
        <div className="team-builder-page">
            <div className="page-header">
                <h1>🛠️ Team Builder</h1>
                <p>Craft the perfect 3v3 composition with AI-powered synergy analysis</p>
            </div>

            <TeamCompositionBuilder />

            <div className="tips-section">
                <h3>💡 Pro Tips</h3>
                <div className="tips-grid">
                    <div className="tip-card">
                        <span className="tip-icon">🎯</span>
                        <h4>Balance is Key</h4>
                        <p>Mix tanks, supports, and damage dealers for versatile compositions</p>
                    </div>

                    <div className="tip-card">
                        <span className="tip-icon">⚡</span>
                        <h4>Super Synergy</h4>
                        <p>Look for brawlers whose supers complement each other</p>
                    </div>

                    <div className="tip-card">
                        <span className="tip-icon">🗺️</span>
                        <h4>Mode Matters</h4>
                        <p>Different game modes favor different team compositions</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TeamBuilder;

/**
 * Counters Page
 * Standalone page for counter-pick analysis
 */

import React from 'react';
import CounterPickWidget from '../components/CounterPickWidget';
import './Counters.css';

const Counters: React.FC = () => {
    return (
        <div className="counters-page">
            <div className="page-header">
                <h1>🎯 Counter-Pick Analysis</h1>
                <p>Find the best brawlers to counter your opponents and dominate the meta</p>
            </div>

            <div className="page-content">
                <CounterPickWidget />
            </div>

            <div className="info-cards">
                <div className="info-card">
                    <h3>📊 Data-Driven</h3>
                    <p>Counter recommendations based on thousands of real battle matchups</p>
                </div>

                <div className="info-card">
                    <h3>🎮 Mode-Specific</h3>
                    <p>Get counters optimized for specific game modes</p>
                </div>

                <div className="info-card">
                    <h3>✨ Confidence Levels</h3>
                    <p>Know which counters are backed by strong sample sizes</p>
                </div>
            </div>
        </div>
    );
};

export default Counters;

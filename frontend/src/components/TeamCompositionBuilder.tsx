/**
 * Team Composition Builder Component
 * Interactive tool for building and analyzing 3v3 team compositions
 */

import React, { useState } from 'react';
import { analyzeSynergy, suggestThirdBrawler, SynergyAnalysis, BrawlerSuggestion } from '../services/api';
import { useToast } from '../context/ToastContext';
import './TeamCompositionBuilder.css';

const TeamCompositionBuilder: React.FC = () => {
    const [selectedBrawlers, setSelectedBrawlers] = useState<string[]>([]);
    const [brawlerInput, setBrawlerInput] = useState('');
    const [analysis, setAnalysis] = useState<SynergyAnalysis | null>(null);
    const [suggestions, setSuggestions] = useState<BrawlerSuggestion[]>([]);
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState('');
    const { showError, showSuccess } = useToast();

    const modes = [
        { value: '', label: 'Global' },
        { value: 'gemGrab', label: 'Gem Grab' },
        { value: 'brawlBall', label: 'Brawl Ball' },
        { value: 'heist', label: 'Heist' },
        { value: 'bounty', label: 'Bounty' },
        { value: 'hotZone', label: 'Hot Zone' },
        { value: 'knockout', label: 'Knockout' },
    ];

    const handleAddBrawler = () => {
        const name = brawlerInput.trim();
        if (!name) return;

        if (selectedBrawlers.length >= 3) {
            showError('Maximum 3 brawlers allowed');
            return;
        }

        if (selectedBrawlers.includes(name)) {
            showError('Brawler already selected');
            return;
        }

        setSelectedBrawlers([...selectedBrawlers, name]);
        setBrawlerInput('');

        // Auto-analyze if we have 2+ brawlers
        if (selectedBrawlers.length >= 1) {
            analyzeCurrentTeam([...selectedBrawlers, name]);
        }
    };

    const handleRemoveBrawler = (index: number) => {
        const newBrawlers = selectedBrawlers.filter((_, i) => i !== index);
        setSelectedBrawlers(newBrawlers);

        if (newBrawlers.length >= 2) {
            analyzeCurrentTeam(newBrawlers);
        } else {
            setAnalysis(null);
            setSuggestions([]);
        }
    };

    const analyzeCurrentTeam = async (brawlers: string[]) => {
        if (brawlers.length < 2) return;

        setLoading(true);
        try {
            const result = await analyzeSynergy(brawlers, mode || undefined);
            setAnalysis(result);

            // Get suggestions if we only have 2 brawlers
            if (brawlers.length === 2) {
                const suggestionResult = await suggestThirdBrawler(
                    brawlers[0],
                    brawlers[1],
                    mode || undefined
                );
                setSuggestions(suggestionResult.suggestions);
            } else {
                setSuggestions([]);
            }
        } catch (error) {
            showError(error instanceof Error ? error.message : 'Failed to analyze team');
            setAnalysis(null);
            setSuggestions([]);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectSuggestion = (suggestion: BrawlerSuggestion) => {
        if (selectedBrawlers.length < 3) {
            const newBrawlers = [...selectedBrawlers, suggestion.brawler_name];
            setSelectedBrawlers(newBrawlers);
            analyzeCurrentTeam(newBrawlers);
            showSuccess(`Added ${suggestion.brawler_name} to your team!`);
        }
    };

    const getSynergyColor = (score: number) => {
        if (score >= 0.65) return '#4CAF50';
        if (score >= 0.55) return '#FFC107';
        if (score >= 0.45) return '#FF9800';
        return '#F44336';
    };

    const getSynergyLabel = (score: number) => {
        if (score >= 0.65) return 'Excellent';
        if (score >= 0.55) return 'Good';
        if (score >= 0.45) return 'Moderate';
        return 'Poor';
    };

    return (
        <div className="team-builder">
            <div className="builder-header">
                <h2>🛠️ Team Composition Builder</h2>
                <p>Build your perfect 3v3 team with AI-powered synergy analysis</p>
            </div>

            <div className="builder-controls">
                <div className="brawler-input-group">
                    <input
                        type="text"
                        className="brawler-input"
                        placeholder="Enter brawler name..."
                        value={brawlerInput}
                        onChange={(e) => setBrawlerInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddBrawler()}
                    />
                    <select
                        className="mode-select"
                        value={mode}
                        onChange={(e) => {
                            setMode(e.target.value);
                            if (selectedBrawlers.length >= 2) {
                                analyzeCurrentTeam(selectedBrawlers);
                            }
                        }}
                    >
                        {modes.map((m) => (
                            <option key={m.value} value={m.value}>
                                {m.label}
                            </option>
                        ))}
                    </select>
                    <button className="add-button" onClick={handleAddBrawler}>
                        Add Brawler
                    </button>
                </div>
            </div>

            <div className="team-slots">
                {[0, 1, 2].map((index) => (
                    <div key={index} className={`team-slot ${selectedBrawlers[index] ? 'filled' : 'empty'}`}>
                        {selectedBrawlers[index] ? (
                            <>
                                <div className="brawler-name">{selectedBrawlers[index]}</div>
                                <button
                                    className="remove-button"
                                    onClick={() => handleRemoveBrawler(index)}
                                >
                                    ✕
                                </button>
                            </>
                        ) : (
                            <div className="empty-slot-text">Slot {index + 1}</div>
                        )}
                    </div>
                ))}
            </div>

            {analysis && (
                <div className="synergy-analysis">
                    <div className="synergy-header">
                        <h3>Team Synergy Analysis</h3>
                        <div
                            className="synergy-score"
                            style={{ color: getSynergyColor(analysis.overall_synergy) }}
                        >
                            <span className="score-value">
                                {(analysis.overall_synergy * 100).toFixed(0)}%
                            </span>
                            <span className="score-label">
                                {getSynergyLabel(analysis.overall_synergy)}
                            </span>
                        </div>
                    </div>

                    {Object.keys(analysis.pairwise_synergies).length > 0 && (
                        <div className="pairwise-section">
                            <h4>Pair Synergies</h4>
                            <div className="pairwise-list">
                                {Object.entries(analysis.pairwise_synergies).map(([pair, score]) => (
                                    <div key={pair} className="pairwise-item">
                                        <span className="pair-name">{pair}</span>
                                        <span
                                            className="pair-score"
                                            style={{ color: getSynergyColor(score) }}
                                        >
                                            {(score * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {analysis.strengths.length > 0 && (
                        <div className="insights-section strengths">
                            <h4>✅ Strengths</h4>
                            <ul>
                                {analysis.strengths.map((strength, idx) => (
                                    <li key={idx}>{strength}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {analysis.weaknesses.length > 0 && (
                        <div className="insights-section weaknesses">
                            <h4>⚠️ Weaknesses</h4>
                            <ul>
                                {analysis.weaknesses.map((weakness, idx) => (
                                    <li key={idx}>{weakness}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {suggestions.length > 0 && selectedBrawlers.length === 2 && (
                <div className="suggestions-section">
                    <h3>🎯 Suggested Third Brawlers</h3>
                    <p className="suggestions-hint">Click to add to your team</p>

                    <div className="suggestions-grid">
                        {suggestions.map((suggestion, idx) => (
                            <div
                                key={idx}
                                className="suggestion-card"
                                onClick={() => handleSelectSuggestion(suggestion)}
                            >
                                <div className="suggestion-rank">#{idx + 1}</div>
                                <div className="suggestion-info">
                                    <div className="suggestion-name">{suggestion.brawler_name}</div>
                                    <div className="suggestion-reason">{suggestion.reasoning}</div>
                                </div>
                                <div className="suggestion-stats">
                                    <div className="synergy-badge">
                                        <span className="stat-value">
                                            {(suggestion.synergy_score * 100).toFixed(0)}%
                                        </span>
                                        <span className="stat-label">Synergy</span>
                                    </div>
                                    <div className={`confidence-badge confidence-${suggestion.confidence}`}>
                                        {suggestion.confidence.toUpperCase()}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {loading && (
                <div className="loading-overlay">
                    <div className="spinner"></div>
                    <p>Analyzing team synergy...</p>
                </div>
            )}
        </div>
    );
};

export default TeamCompositionBuilder;

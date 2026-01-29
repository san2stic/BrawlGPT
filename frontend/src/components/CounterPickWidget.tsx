/**
 * Counter-Pick Widget Component
 * Displays the best counter-picks for a specific brawler
 */

import React, { useState } from 'react';
import { getCounterPicks, CounterPick } from '../services/api';
import { useToast } from '../context/ToastContext';
import './CounterPickWidget.css';

interface CounterPickWidgetProps {
    initialBrawler?: string;
    mode?: string;
}

const CounterPickWidget: React.FC<CounterPickWidgetProps> = ({ initialBrawler, mode }) => {
    const [brawlerName, setBrawlerName] = useState(initialBrawler || '');
    const [counters, setCounters] = useState<CounterPick[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedMode, setSelectedMode] = useState(mode || '');
    const { showError } = useToast();

    const modes = [
        { value: '', label: 'Global' },
        { value: 'gemGrab', label: 'Gem Grab' },
        { value: 'brawlBall', label: 'Brawl Ball' },
        { value: 'heist', label: 'Heist' },
        { value: 'bounty', label: 'Bounty' },
        { value: 'hotZone', label: 'Hot Zone' },
        { value: 'knockout', label: 'Knockout' },
    ];

    const handleSearch = async () => {
        if (!brawlerName.trim()) {
            showError('Please enter a brawler name');
            return;
        }

        setLoading(true);
        try {
            const response = await getCounterPicks(brawlerName, selectedMode || undefined);
            setCounters(response.counters);

            if (response.counters.length === 0 && response.message) {
                showError(response.message);
            }
        } catch (error) {
            showError(error instanceof Error ? error.message : 'Failed to get counters');
            setCounters([]);
        } finally {
            setLoading(false);
        }
    };

    const getConfidenceColor = (confidence: string) => {
        switch (confidence) {
            case 'high': return 'var(--accent-success)';
            case 'medium': return 'var(--accent-warning)';
            case 'low': return 'var(--text-secondary)';
            default: return 'var(--text-secondary)';
        }
    };

    return (
        <div className="counter-pick-widget">
            <div className="widget-header">
                <h3>🎯 Counter-Pick Finder</h3>
                <p className="widget-description">Find the best brawlers to counter your opponent</p>
            </div>

            <div className="search-section">
                <div className="input-group">
                    <input
                        type="text"
                        className="brawler-input"
                        placeholder="Enter brawler name (e.g., Edgar)"
                        value={brawlerName}
                        onChange={(e) => setBrawlerName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />

                    <select
                        className="mode-select"
                        value={selectedMode}
                        onChange={(e) => setSelectedMode(e.target.value)}
                    >
                        {modes.map((m) => (
                            <option key={m.value} value={m.value}>
                                {m.label}
                            </option>
                        ))}
                    </select>

                    <button
                        className="search-button"
                        onClick={handleSearch}
                        disabled={loading}
                    >
                        {loading ? 'Searching...' : 'Find Counters'}
                    </button>
                </div>
            </div>

            {counters.length > 0 && (
                <div className="counters-list">
                    <div className="list-header">
                        <h4>Top Counters for {brawlerName}</h4>
                        <span className="mode-badge">{selectedMode || 'Global'}</span>
                    </div>

                    {counters.map((counter, idx) => (
                        <div key={idx} className="counter-card">
                            <div className="counter-rank">#{idx + 1}</div>

                            <div className="counter-info">
                                <div className="counter-name">{counter.brawler_name}</div>
                                <div className="counter-reason">{counter.reasoning}</div>
                            </div>

                            <div className="counter-stats">
                                <div className="win-rate">
                                    <span className="stat-value">{(counter.win_rate * 100).toFixed(1)}%</span>
                                    <span className="stat-label">Win Rate</span>
                                </div>

                                <div className="confidence-badge" style={{ color: getConfidenceColor(counter.confidence) }}>
                                    {counter.confidence.toUpperCase()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!loading && counters.length === 0 && brawlerName && (
                <div className="no-results">
                    <span>🔍</span>
                    <p>No matchup data available</p>
                </div>
            )}
        </div>
    );
};

export default CounterPickWidget;

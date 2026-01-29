import React, { useEffect, useState } from 'react';

// Define types for the analysis data
interface Connection {
    name: string;
    tag: string;
    synergy: 'excellent' | 'good' | 'neutral' | 'bad';
    stats: {
        total: number;
        wins: number;
        losses: number;
        winRate: number;
        favoriteMode: string | null;
    };
}

interface AnalysisData {
    total_battles_analyzed: number;
    teammates: Connection[];
}

interface NetworkGraphProps {
    playerTag: string;
}

const NetworkGraph: React.FC<NetworkGraphProps> = ({ playerTag }) => {
    const [data, setData] = useState<AnalysisData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [hoveredNode, setHoveredNode] = useState<Connection | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!playerTag) return;

            try {
                setLoading(true);
                // Clean tag just to be safe (remove #)
                const cleanTag = playerTag.replace('#', '');
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/player/${cleanTag}/connections`);

                if (!response.ok) {
                    throw new Error('Failed to fetch connections data');
                }

                const result = await response.json();
                setData(result.analysis);
            } catch (err) {
                console.error("Error fetching graph data:", err);
                setError("Could not load player interactions.");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [playerTag]);

    if (loading) return <div className="p-8 text-center text-gray-400 animate-pulse">Analysing battle history...</div>;
    if (error) return <div className="p-8 text-center text-red-400">{error}</div>;
    if (!data || data.teammates.length === 0) return <div className="p-8 text-center text-gray-400">No team history found in recent battles.</div>;

    // --- Graph Layout Calculation ---
    // We place the main player in the center, and teammates in a circle around.
    // We limit to top 16 connections to avoid clutter.
    const topConnections = data.teammates.slice(0, 16);
    const radius = 120; // Radius of the circle
    const centerX = 150;
    const centerY = 150;

    const nodes = topConnections.map((conn, index) => {
        const angle = (index / topConnections.length) * 2 * Math.PI;
        return {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
            ...conn
        };
    });

    const getSynergyColor = (synergy: string) => {
        switch (synergy) {
            case 'excellent': return '#4ade80'; // green-400
            case 'good': return '#22d3ee'; // cyan-400
            case 'bad': return '#f87171'; // red-400
            default: return '#fbbf24'; // amber-400 (neutral)
        }
    };

    return (
        <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700 mt-6">
            <h2 className="text-2xl font-bold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
                Network & Synergy
            </h2>

            <div className="flex flex-col md:flex-row gap-8">

                {/* Interaction Graph */}
                <div className="flex-1 flex justify-center items-center relative min-h-[320px]">
                    <svg width="300" height="300" className="overflow-visible">
                        {/* Links */}
                        {nodes.map((node, i) => (
                            <line
                                key={`link-${i}`}
                                x1={centerX}
                                y1={centerY}
                                x2={node.x}
                                y2={node.y}
                                stroke={getSynergyColor(node.synergy)}
                                strokeWidth={hoveredNode === node ? 3 : 1}
                                opacity={0.6}
                            />
                        ))}

                        {/* Center Node (You) */}
                        <circle cx={centerX} cy={centerY} r="25" fill="#8b5cf6" stroke="#fff" strokeWidth="2" />
                        <text x={centerX} y={centerY} dy=".3em" textAnchor="middle" fill="white" className="text-xs font-bold pointer-events-none">YOU</text>

                        {/* Teammate Nodes */}
                        {nodes.map((node, i) => (
                            <g
                                key={`node-${i}`}
                                onMouseEnter={() => setHoveredNode(node)}
                                onMouseLeave={() => setHoveredNode(null)}
                                className="cursor-pointer transition-transform hover:scale-110"
                            >
                                <circle
                                    cx={node.x}
                                    cy={node.y}
                                    r={Math.max(10, Math.min(20, node.stats.total * 3))} // Size based on games played
                                    fill={getSynergyColor(node.synergy)}
                                    stroke="#1f2937"
                                    strokeWidth="2"
                                />
                                {/* Initial */}
                                <text x={node.x} y={node.y} dy=".3em" textAnchor="middle" fill="#1f2937" className="text-[10px] font-bold pointer-events-none uppercase">
                                    {node.name.substring(0, 2)}
                                </text>
                            </g>
                        ))}
                    </svg>

                    {/* Tooltip / Legend Overlay */}
                    {hoveredNode && (
                        <div className="absolute bottom-0 left-0 right-0 bg-gray-900/90 p-3 rounded-lg border border-gray-600 text-sm backdrop-blur-sm animate-fade-in">
                            <div className="font-bold text-white mb-1">{hoveredNode.name} <span className="text-gray-400 font-normal">({hoveredNode.tag})</span></div>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                                <span className="text-gray-300">Games: <span className="text-white">{hoveredNode.stats.total}</span></span>
                                <span className="text-gray-300">Win Rate: <span className={{
                                    'excellent': 'text-green-400',
                                    'good': 'text-cyan-400',
                                    'neutral': 'text-amber-400',
                                    'bad': 'text-red-400'
                                }[hoveredNode.synergy]}>{hoveredNode.stats.winRate}%</span></span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Detailed Stats Panel */}
                <div className="flex-1 space-y-4">
                    <div className="bg-gray-700/50 p-4 rounded-lg">
                        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Top Partners</h3>
                        <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                            {data.teammates.slice(0, 10).map((mate, i) => (
                                <div key={i} className="flex justify-between items-center text-sm p-2 hover:bg-white/5 rounded transition-colors group">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${mate.synergy === 'excellent' ? 'bg-green-400' : mate.synergy === 'bad' ? 'bg-red-400' : 'bg-amber-400'}`}></div>
                                        <span className="font-medium text-gray-200">{mate.name}</span>
                                    </div>
                                    <div className="text-right">
                                        <div className={`font-bold ${mate.synergy === 'bad' ? 'text-red-400' : 'text-green-400'}`}>
                                            {mate.stats.winRate}%
                                        </div>
                                        <div className="text-xs text-gray-500">{mate.stats.total} games</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="text-xs text-gray-500 text-center">
                        Based on {data.total_battles_analyzed} recent battles
                    </div>
                </div>

            </div>
        </div>
    );
};

export default NetworkGraph;

import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Brain, Sparkles, Loader2, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface MetaReport {
    most_popular_brawlers: { name: string; count: number; frequency: string }[];
    analyzed_matches: number;
}

interface AnalysisResult {
    meta_report: MetaReport;
    ai_analysis: string;
}

export default function MetaAnalysis({ playerTag }: { playerTag: string }) {
    const { token, isAuthenticated } = useAuth();
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const runAnalysis = async () => {
        // Validation check removed as it relied on process.env which is not available
        if (!token) {
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/api/crawler/analyze/${encodeURIComponent(playerTag)}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Analysis failed");
            }

            const data = await response.json();
            setResult(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 backdrop-blur-sm mt-8 relative overflow-hidden group">
                <div className="absolute -right-10 -top-10 w-40 h-40 bg-purple-500/20 rounded-full blur-3xl group-hover:bg-purple-500/30 transition-all duration-500"></div>
                <div className="flex flex-col items-center text-center z-10 relative">
                    <Brain className="w-12 h-12 text-purple-400 mb-4" />
                    <h3 className="text-xl font-bold text-white mb-2">Brawl Advanced Intelligence</h3>
                    <p className="text-slate-400 mb-4 max-w-md">
                        Log in to unlock deep meta analysis powered by Gemini Flash 1.5. Crawl your battles and find the perfect counter-strategies.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 backdrop-blur-sm mt-8 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-purple-500/10 rounded-2xl">
                    <Brain className="w-6 h-6 text-purple-400" />
                </div>
                <h2 className="text-2xl font-bold text-white">Advanced Meta Intelligence</h2>
                <div className="ml-auto px-3 py-1 bg-purple-500/20 text-purple-300 text-xs font-bold rounded-full border border-purple-500/30 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    GEMINI FLASH
                </div>
            </div>

            {!result && !loading && (
                <div className="text-center py-8">
                    <p className="text-slate-400 mb-6">
                        Analyze your last 25 battles to detect the current meta in your trophy range and get personalized counter-picks.
                    </p>
                    <button
                        onClick={runAnalysis}
                        className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-purple-900/20 transition-all transform hover:scale-105 flex items-center gap-2 mx-auto"
                    >
                        <Sparkles className="w-5 h-5" />
                        Run Deep Analysis
                    </button>
                </div>
            )}

            {loading && (
                <div className="text-center py-12">
                    <Loader2 className="w-10 h-10 text-purple-500 animate-spin mx-auto mb-4" />
                    <p className="text-purple-300 font-medium animate-pulse">Crawling Battle Logs...</p>
                    <p className="text-slate-500 text-sm mt-2">Analyzing opponents & teammates</p>
                </div>
            )}

            {error && (
                <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-xl flex items-center gap-3 mb-6">
                    <AlertTriangle className="w-5 h-5" />
                    <p>{error}</p>
                </div>
            )}

            {result && (
                <div className="space-y-6 animate-fade-in">
                    {/* Brawler Frequency Chart (Simplified) */}
                    <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800">
                        <h4 className="text-sm font-bold text-slate-400 mb-3 uppercase tracking-wider">Most Encountered Brawlers</h4>
                        <div className="space-y-3">
                            {result.meta_report.most_popular_brawlers.slice(0, 5).map((item, index) => (
                                <div key={index} className="flex items-center gap-3">
                                    <span className="w-6 text-slate-500 font-mono text-sm">#{index + 1}</span>
                                    <div className="flex-1">
                                        <div className="flex justify-between items-center mb-1">
                                            <span className="font-bold text-slate-200">{item.name}</span>
                                            <span className="text-xs text-purple-400">{item.frequency}</span>
                                        </div>
                                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-purple-500 rounded-full"
                                                style={{ width: item.frequency }}
                                            ></div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Gemini Analysis */}
                    <div className="bg-slate-900/80 p-6 rounded-xl border border-purple-500/20 prose prose-invert max-w-none prose-p:text-slate-300 prose-headings:text-white prose-strong:text-purple-300 prose-ul:text-slate-300 prose-li:marker:text-purple-500">
                        <ReactMarkdown>
                            {result.ai_analysis}
                        </ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
}
